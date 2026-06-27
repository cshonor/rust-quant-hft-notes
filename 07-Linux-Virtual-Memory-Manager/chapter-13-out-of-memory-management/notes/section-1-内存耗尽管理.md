# Ch 13 内存耗尽管理 · Out of Memory Management

> **Understanding the Linux Virtual Memory Manager** · Mel Gorman · **跳过**（HFT：**生产 latency 机** 应 **never 触发 OOM** — 足够 RAM + **`mlock`** + 监控；本章解释 **谁会被杀、为何突然 SIGKILL**）

原书 **故意写短** — OOM 管理器任务单一：

```
有足够内存？ → 否且回收已尽力 → 真 OOM？ → 选进程 → 杀死 → 释放内存
```

> **源码入口（Ch 1 阅读路线第 1 步）：** [`mm/oom_kill.c`](https://elixir.bootlin.com/linux/latest/source/mm/oom_kill.c) — 牵涉 **zone 水位、回收、swap、mm_struct** 等多处，但 **控制流相对集中**，适合 **第一次读 `mm/`**。

> **现代扩展：** **cgroup v1/v2 memory** 的 **memcg OOM**、**`oom_score_adj`**、**pid 1 保护** 等 — 原书 **`badness()`** 思路仍在，细节以当前树为准。

→ 回收失败背景：[Ch 10](../../chapter-10-page-frame-reclamation/notes/section-1-页框回收.md) · **`PF_MEMDIE`**：[Ch 6](../../chapter-06-physical-page-allocation/notes/section-1-物理页分配.md#4-gfp-标志与进程标志-gfp--process-flags) · **`VM_ACCOUNT`**：[Ch 12](../../chapter-12-shared-memory-virtual-filesystem/notes/section-1-共享内存虚拟文件系统.md#5-26-内核的新变化)

---

## 本章在 VM 子系统中的位置

```
Ch 6 alloc 失败 / Ch 10 shrink 扫尽仍不够
        ↓
Ch 13 out_of_memory() → select → kill
        ↓
物理页、swap cache、页表、struct page 随进程退出归还
```

**HFT：** OOM killer **按 badness 选「大内存、年轻进程」** — 未 **`mlock`** 的 **大 heap 交易进程** 可能是 **牺牲品**；与 **策略无关**，纯 **内核启发式**。

---

## 1. 检查可用内存 (`vm_enough_memory`)

在 **可能大幅消耗 VA/RSS** 的操作 **之前** **主动检查** — 尽量避免滑入 OOM：

| 触发场景（例） | 系统调用 / 路径 |
|----------------|-----------------|
| 扩展堆 | **`brk()`** |
| 扩大映射 | **`mremap()`** |

**`vm_enough_memory()`** 估算 **潜在可用内存** 是否 ≥ 本次请求：

| 计入（原书） | 说明 |
|--------------|------|
| **页缓存** 中可回收部分 | clean cache 等 |
| **空闲物理页** | Buddy free |
| **空闲 swap 槽** | 尚未承诺的 swap |
| **未用 dcache / inode cache** | 可 shrink（Ch 10 §4） |

**Overcommit：** 若管理员允许 **内存超额分配**（**`vm.overcommit_memory`** 等），检查 **更松** — **承诺的 VA** 可大于 **物理+swap**，**OOM 风险上升**。

**HFT：** **`overcommit_memory=2`** + 合理 **`overcommit_ratio`** 更 **可预测** — 仍 **不能替代** 物理 RAM + **`mlock`**。

---

## 2. 确定 OOM 状态 (`out_of_memory`)

**触发条件（概念）：** 内存不足 + **页面回收已在最高压力** 下仍 **无法释放足够页** → 调用 **`out_of_memory()`**。

### 防误杀：以下 **任一** 成立 → **认为尚未真 OOM**（暂不杀）

| 条件 | 意图 |
|------|------|
| **仍有 swap 空间** | 还可 **swap out**，不必立刻杀人 |
| 距 **上次 alloc 失败** **> 5s** |  transient 故障可能已恢复 |
| **过去 1s 内无 alloc 失败** | 避免 **偶发失败** 触发 |
| **过去 5s 内 alloc 失败 < 10 次** | 失败 **不够持续** |
| **过去 5s 内已杀过 OOM 进程** | 等 **受害者释放内存** 生效 |

**直觉：** 区分 **「I/O 慢 / 回收进行中」** 与 **「真的没人可杀了」** — 原书 **启发式**，现代仍有 **类似 throttle**。

---

## 3. 选择要杀死的进程 (`select_bad_process` / `badness`)

遍历进程，**`badness()` 打分** — **最高分** 为牺牲品。

### 打分（原书算法直觉）

```
badness ∝  Total VM（虚拟内存占用大）
         ─────────────────────────────
         sqrt(CPU 运行时间)           （运行久 → 分母大 → 分数低）
```

| 倾向 | 原因 |
|------|------|
| **杀大内存、短寿命进程** | 突然 **malloc 暴涨** 的 **更可疑** |
| **少杀长期 daemon** | 老进程 **不一定是** 本次 OOM 根因 |

### 权限保护（分数 ÷ 4）

| 进程 | 保护 |
|------|------|
| **root** | 降低被杀概率 |
| **`CAP_SYS_ADMIN`** | 同上 |
| **`CAP_SYS_RAWIO`** | 直接硬件访问 — **更不应误杀** |

**现代：** **`/proc/<pid>/oom_score_adj`**（-1000 ~ 1000）— 用户态 **显式调节**；**cgroup** 可 **禁用/隔离** OOM。

**HFT：** 关键进程设 **`oom_score_adj=-1000`**（或 cgroup **oom_kill_disable**）— **不能防 swap/reclaim stall**，只防 **被选中杀死**。

---

## 4. 杀死选定的进程

选中后：

| 步骤 | 说明 |
|------|------|
| **通知范围** | 该 **task** + **共享同一 `mm_struct` 的所有线程** |
| **调度优先** | 提高优先级 — **尽快退出释内存** |
| **内存标志** | **`PF_MEMALLOC` + `PF_MEMDIE`** — 退出路径 **仍可分配** 必要页（Ch 6） |
| **信号选择** | 有 **`CAP_SYS_RAWIO`** → **`SIGTERM`**（优雅）；否则 **`SIGKILL`** |

**日志：** dmesg 常见 **`Out of memory: Kill process <pid> (<comm>) score …`** — 运维 **定位谁被杀**。

---

## 5. 2.6 内核的新变化

| 变化 | 目的 |
|------|------|
| **`VM_ACCOUNT` VMA**（Ch 12） | 对 **shmem 等** 操作 **额外检查** 可用内存 |
| **严格 overcommit 上限** | **`committed_AS ≤ 总RAM × (overcommit_ratio/100) + 总swap`** — **尽量不让系统走到 OOM killer** |

**哲学：** **记账前移** — 在 **承诺内存时** 就拒绝，而非 **用尽后杀人**。

---

## OOM 决策简图

```
alloc / brk / mremap 大请求
    vm_enough_memory? ──否──► 可能 early fail（视 overcommit）
        │
内存压力 ↑
    kswapd + direct reclaim 尽力
        │
仍失败 → out_of_memory()
    防误杀检查 ──跳过──► 返回，稍后重试
        │
    select_bad_process() / badness
        │
    SIGKILL / SIGTERM → 进程退出 → 页框归还
```

---

## HFT 精读 checklist

| 手段 | 目的 |
|------|------|
| **足够物理 RAM** | 根本 — OOM = 已 **设计失败** |
| **`mlock` 关键映射** | 减 **RSS 被回收**；**不防** 他进程 OOM |
| **`oom_score_adj=-1000`** | 降低 **交易主进程** 被杀概率 |
| **cgroup memory limit** | 隔离 **非关键** 服务，**别拖全局 OOM** |
| **监控 dmesg / kernel oom** | 事后 **comm + score** |
| **Ch 1 读源码** | **`oom_kill.c`** 是 **进 mm/ 的第一站** — 串联 Ch 2 水位、Ch 10 回收、Ch 6 GFP |

---

## 相关章节

- 上一章：[../../chapter-12-shared-memory-virtual-filesystem/notes/section-1-共享内存虚拟文件系统.md](../../chapter-12-shared-memory-virtual-filesystem/notes/section-1-共享内存虚拟文件系统.md)
- 下一章：[../../chapter-14-the-final-word/notes/section-1-结束语.md](../../chapter-14-the-final-word/notes/section-1-结束语.md)
- 附录 M：[appendix-M-内存耗尽管理.md](../../appendix-M-内存耗尽管理.md)
- Ch 1 阅读路线：[../../chapter-01-introduction/notes/section-1-简介.md](../../chapter-01-introduction/notes/section-1-简介.md#4-阅读代码的策略-reading-the-code)

---
