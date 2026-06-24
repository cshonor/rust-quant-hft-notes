# Ch 4 · 进程调度 · Process Scheduling

> **Linux Kernel Development 3rd** · Robert Love · **精读**  
> 本章定位：**谁跑、何时跑、跑多久** — 抢占式多任务、**CFS**、休眠/唤醒、内核抢占、**RT 策略** 与 **affinity** syscall。HFT **绑核 / `SCHED_FIFO` / 抖动** 的底层地图。

---

## 本节结构

| 节 | 主题 | 带走什么 |
|----|------|----------|
| **① 演进** | 抢占式多任务 | O(1) → **CFS（2.6.23）** |
| **② 策略** | I/O vs CPU 型 · 优先级 | **nice** · **RT 0–99** |
| **③ CFS** | 公平调度算法 | **`vruntime`** · **红黑树** |
| **④ 休眠唤醒** | 等待队列 | `wake_up()` |
| **⑤ 抢占与切换** | `context_switch` | **用户/内核抢占** |
| **⑥ RT 策略** | FIFO / RR | **软实时** |
| **⑦ syscall** | 调参接口 | **affinity · yield** |

---

### ① 多任务与调度器演进

Linux = **抢占式多任务（Preemptive Multitasking）**：

| 概念 | 含义 |
|------|------|
| **调度器** | 决定 **哪个进程运行、何时、多久** |
| **抢占** | 强制停掉当前任务，换另一个上 CPU |

#### 历史脉络

```
简单调度器
    │
    ▼
O(1) 调度器（2.5）── 大服务器扩展性好；交互/低延迟场景欠佳
    │
    ▼
CFS（2.6.23+）────── 默认公平调度，兼顾交互响应
```

| 调度器 | 特点 |
|--------|------|
| **O(1)** | 每 CPU 固定时间片数组 — **O(1)** 选下一个；海量任务可扩展 |
| **CFS** | **完全公平** — 按权重分 CPU **比例**，非固定绝对时间片 |

→ [02 SysPerf §3.2 O(1)→CFS](../../02-Systems-Performance-2nd/chapter-03-operating-systems/notes/section-3.2-内核基础与核心概念.md) · [§6.4 CFS/affinity](../../02-Systems-Performance-2nd/chapter-06-cpus/notes/section-6.4-硬件与软件架构.md)

---

### ② 调度策略 · Policy

#### I/O 消耗型 vs 处理器消耗型

| 类型 | 行为 | 调度诉求 |
|------|------|----------|
| **I/O 消耗型** | 大量等磁盘/网络/输入 | **快响应** — GUI、shell |
| **处理器消耗型** | 大量跑代码 | **公平分 CPU** — 编码、批处理 |

**Linux 倾向照顾 I/O 型** — 改善交互体验（CFS 通过 `vruntime` 增长慢等方式体现）。

**HFT：** 行情线程常 **CPU 型 + 忙等/轮询**；要与 **ksoftirq、CFS 重平衡、 housekeeping** 隔离 — **affinity + RT 策略**。

#### 两套优先级

| 类型 | 范围 | 规则 |
|------|------|------|
| **nice** | **-20 ~ +19**（默认 **0**） | 值 **越低** 优先级 **越高** — 影响 **CFS 权重 / CPU 份额** |
| **实时优先级** | **0 ~ 99**（默认档） | 值 **越高** 优先级 **越高** — **任一 RT > 所有普通进程** |

#### 时间片 vs CFS

| 传统 | CFS |
|------|-----|
| 分配 **固定绝对时间片** | **不直接分配时间片** |
| | 用 **nice 作权重**，分 **处理器使用比例** |

---

### ③ Linux 调度算法 · CFS

**理念：** 模拟 **理想、完美的多任务 CPU** — 每进程 **精确获得按权重比例的平均 CPU 时间**。

#### 时间记账 · `sched_entity` · `vruntime`

| 字段/概念 | 作用 |
|-----------|------|
| **`sched_entity`** | CFS 调度实体（进程/线程在运行队列中的表示） |
| **`vruntime`（虚拟运行时间）** | 记录 **实际运行时间**，按可运行进程数 **加权标准化** |
| 不用传统时间片 | 比较的是 **谁跑得「相对少」** |

```
权重高（nice 低）的进程 ──► 同样物理运行时间，vruntime 涨得慢
权重低的进程 ──────────► vruntime 涨得快
```

#### 进程选择

| 规则 | 实现 |
|------|------|
| **选 `vruntime` 最小者运行** | 最「欠账」、最该分到 CPU |
| 数据结构 | **红黑树** 管理所有 **可运行** 实体 |
| 下一个任务 | 树 **最左节点** |

```
        红黑树（按 vruntime）
              ┌───┐
           ┌──┤   ├──┐
           │  └───┘  │
    最左 ◄─┤  最小 vruntime  ──► 下次运行
           └─────────┘
```

→ **Ch 6** 红黑树在内核中的其他用途

---

### ④ 休眠与唤醒 · Sleeping and Waking Up

进程等事件（磁盘 I/O、键盘…）时：

| 步骤 | 动作 |
|------|------|
| 1 | 标为 **`TASK_INTERRUPTIBLE`** 或 **`TASK_UNINTERRUPTIBLE`** |
| 2 | 从 CFS **红黑树移除** |
| 3 | 挂到 **等待队列（Wait Queue）** |

事件就绪时：

| 步骤 | 动作 |
|------|------|
| 1 | **`wake_up()`**（及变体）遍历等待队列 |
| 2 | 状态 → **`TASK_RUNNING`** |
| 3 | **重新插入红黑树** — 参与 CFS 竞争 |

```
RUNNING ──睡眠──► 移出红黑树 ──► wait queue
                                    │
              wake_up ◄── 事件完成 ──┘
                 │
                 └──► RUNNING + 插回红黑树
```

→ **Ch 3** 五态 · **Ch 9–10** 等待队列与锁

---

### ⑤ 抢占与上下文切换

#### `context_switch()`

| 切换内容 | 说明 |
|----------|------|
| **虚拟内存** | 页表 / `mm_struct` |
| **处理器状态** | 寄存器、PC、栈指针等 |

#### `need_resched`

内核用 **`need_resched`** 标志 — 「该调度了」→ 在安全点调用调度器。

#### 用户抢占 vs 内核抢占

| 类型 | 时机 |
|------|------|
| **用户抢占** | 从 **内核返回用户空间前** — 可换掉当前任务 |
| **内核抢占**（2.6+） | 内核代码 **未持锁 / 可抢占点** 时 — **内核态也可被抢占** |

```
内核路径：
  中断/定时器 ──► 设 need_resched
       │
  抢占点（返回用户态 / preempt_enable / 调度器调用）
       │
       └──► schedule() ──► context_switch()
```

**HFT：** **内核抢占 + 长临界区** → 调度延迟；`PREEMPT_RT`、短锁、绑核隔离是工程回应。→ **Ch 1** 宏内核+抢占

→ [08-1 Day 16 多任务/切换](../../08-system-low-level-hands-on/08-1-30days-os/notes/day-16-多任务2.md)

---

### ⑥ 实时调度策略 · Real-Time

RT 进程由 **独立实时调度器** 管理 — **不走 CFS 红黑树**。

| 策略 | 行为 |
|------|------|
| **`SCHED_FIFO`** | 先进先出 — **无时间片**；同优先级先运行直到 **阻塞或 yield** |
| **`SCHED_RR`** | 轮转 — 同优先级带 **时间片**，用完排回队尾 |

#### 软实时 · Soft Real-time

| 承诺 | 说明 |
|------|------|
| Linux **尽力** 在期限内调度 RT 任务 | |
| **无硬性绝对保证** | 不同于硬实时 OS |

**HFT 实盘：** 关键线程常用 **`SCHED_FIFO` + 高 RT 优先级 + `sched_setaffinity`**；慎滥用 — 饿死 CFS 线程会导致 **系统管理/日志/网卡慢路径** 失灵。

→ [07-TLPI Ch 34–37](../../07-The-Linux-Programming-Interface/) · [03 架构课 a09 调度](../../05-Linux-Kernel-Development/03_Course_Kernel_Architecture/CHECKLIST.md)

---

### ⑦ 与调度相关的系统调用

| 系统调用 | 作用 |
|----------|------|
| **`nice()`** | 设置 **nice** — 改 CFS 权重 |
| **`sched_setscheduler()`** | 改 **调度策略**（`SCHED_OTHER` / `FIFO` / `RR` …）及 RT 优先级 |
| **`sched_setaffinity()`** | **CPU 亲和性** — 限制在哪些核上跑 |
| **`sched_yield()`** | **主动让出** CPU — 同优先级重新排队 |

#### 用户态常用包装

```bash
nice -n 10 ./worker          # 降低 CFS 权重
taskset -c 2,3 ./gateway     # 绑核 2、3
chrt -f 80 ./hot_thread      # SCHED_FIFO 优先级 80
```

| 工具 | 对应 |
|------|------|
| **`taskset`** | `sched_setaffinity` |
| **`chrt`** | `sched_setscheduler` |

→ [02 SysPerf §6.9 CPU 调优](../../02-Systems-Performance-2nd/chapter-06-cpus/notes/section-6.9-CPU-调优.md)

---

### Ch 4 小结

| 问题 | 答案 |
|------|------|
| Linux 多任务？ | **抢占式** — 调度器可强制切换 |
| 默认调度器？ | **CFS** — 公平 **比例**，非固定片长 |
| CFS 选谁？ | **`vruntime` 最小** — **红黑树最左** |
| nice vs RT？ | nice 调 **份额**；RT **0–99 压过** 所有普通进程 |
| 睡眠去哪？ | **等待队列** — 唤醒后回红黑树 |
| 内核能抢占吗？ | **能**（2.6+）— 持锁等 **非抢占** 区除外 |
| RT 策略？ | **`SCHED_FIFO` / `SCHED_RR`** — **软实时** |
| HFT 三板斧？ | **`affinity` + `chrt` + 隔离核** |

---

### 检查单

- [ ] 解释 **CFS 为何不分配传统时间片**，`vruntime` 何意
- [ ] 区分 **nice** 与 **RT 优先级** 两套数值方向
- [ ] 画出 **睡眠 → wait queue → wake_up → 红黑树**
- [ ] 说出 **`sched_setaffinity` / `sched_yield`** 用途
- [ ] 知 **软实时** 边界 — 生产上如何配 **FIFO + 绑核** 且不伤系统

---

## 相关章节

- 上一章：[chapter-03-进程管理.md](./chapter-03-进程管理.md)
- 下一章：[chapter-05-系统调用.md](./chapter-05-系统调用.md)
- 本模块导读：[README.md](./README.md) · [OUTLINE.md](./OUTLINE.md)
