# Ch 16 案例研究 · Case Study

> **Systems Performance 2nd** · Brendan Gregg · **选读**（🟡 全书收官 · 新手可先读作「预告片」）

> 本章定位：**全书大阅兵** — 无新基础理论，用 Netflix 生产案例 **「An Unexplained Win（无法解释的性能提升）」** 串起 Ch 2 方法论 + Ch 6–11 资源视角 + Ch 13–15 工具链。  
> **Gregg 建议：** 新手 **可先读本章** 当实战预览，读完理论后再 **重温** — 第二次读会认出每一步对应的章。  
> **HFT：** 「为什么突然变快了」与「为什么变慢」 **同样值得查** — 暴露隐藏瓶颈、错误 baseline、或邻居/配置变化。

---

## 大白话 · 本章就一件事

> **一个云生产谜题：系统莫名变快了 — 用全书套路把它讲清楚。**

不是新工具教程，而是一条 **可复制的排查叙事**：

```
问题陈述 → 策略（别乱试）
  → 统计 + 静态配置（浅层）
  → PMC + 软件事件（硬件/内核计数）
  → 动态追踪 + 栈（细粒度）
  → 结论（Drill-Down 拼拼图）
```

下面按原书 **16.1.1–16.1.8** 展开，并映射到本 handbook 各章。

---

## 案例背景：An Unexplained Win

### 为什么「变快了」也要查？

| 「变慢」 | 「变快（Unexplained Win）」 |
|----------|----------------------------|
| 用户投诉、SLA 破 | 常被忽略 — 「反正好了」 |
| 驱动紧急排查 | **同样暴露机制** — 你不懂为何快，就不懂何时会再慢 |

**可能真相类型：**

- 负载变了（邻居搬走、流量降）
- 配置/部署变了（内核、库、JVM、sysctl）
- 缓存/预热状态变了
- 测量方式变了（指标口径、采样窗口）
- **真正优化** — 但需 **证据链** 证明是哪一层

**HFT 类比：**

- 上线新版本后 **P99 tick 突然好 20%** — 是策略改好了，还是 **共置邻居撤了**、**THP 关了**、**绑核终于生效**？
- 不搞清楚 → 下次回归 **无法复现「赢」**。

→ Ch 2 [反面方法](./chapter-02-方法论.md) · Ch 12 [基准与拷问](./chapter-12-基准测试.md)

---

## 16.1.1–16.1.2 问题陈述与分析策略

### 问题陈述（Problem Statement）

好的陈述 **可验证、可范围化**：

| 要素 | Netflix 案例精神 | HFT 模板 |
|------|------------------|----------|
| **现象** | 吞吐/延迟相对 baseline **莫名改善** | tick P99 / 发单 RTT 相对昨日 |
| **范围** | 哪类实例、哪区域、哪时间段 | 哪进程、哪核、哪交易所 session |
| **回归点** | 与何时、何变更对比 | 与哪次 commit / 哪台机器 |
| **非目标** | 先不假设根因 | 先不「再调一个参数」 |

**反模式（Ch 2）：**

- ❌ **路灯法** — 只查熟悉的 CPU%
- ❌ **随机变更法** — 没假设就改 sysctl
- ✅ **假设 → 观测验证 → 缩小范围**

### 分析策略（Analysis Strategy）

```
1. 列出 2–3 个 competing hypotheses（竞争假设）
2. 选 **开销最低** 的观测先否定/支持
3. Drill-Down：系统 → 资源 → 栈 → 代码
4. 记录每步证据 — 可写 postmortem
```

**全书方法论入口：** Ch 2 USE/RED、延迟分解、工作负载 vs 资源分析。

→ [chapter-02-方法论.md](./chapter-02-方法论.md)

---

## 16.1.3–16.1.4 统计数据与静态配置

### 常规统计（Statistics）— 由浅入深第一步

**目的：** 建立 **baseline 对比** — 「变快」是相对什么？

| 层级 | 工具/数据 | 对应章 |
|------|-----------|--------|
| 全局 | `uptime`、`vmstat`、`mpstat`、`iostat`、`sar` | Ch 6–9 |
| 网络 | `ss`、`ip -s link`、`nstat` | Ch 10 |
| 云/租户 | steal time、cgroup throttle | Ch 11 |
| 历史 | **sar 归档** — 案发前后 | 附录 B |

**要问：**

- 利用率是 **真降** 还是 **测量窗口变**？
- 负载 **workload** 变轻了吗？（Ch 2 工作负载分析）
- 邻居/流量是否 **同时段不可比**？

### 静态配置（Configuration）

**部署/环境 diff：**

| 类别 | 检查项 |
|------|--------|
| 内核 | 版本、cmdline、mitigations |
| sysctl | 网络/VM（Ch 10/7） |
| 实例类型 | AWS 机型、NUMA、CPU credits |
| 应用 | 库版本、GC、线程池、绑核 |
| 挂载/FS | noatime、磁盘类型 |

**HFT checklist：**

```
[ ] 内核/驱动版本 vs baseline
[ ] isolcpus / IRQ affinity / governor
[ ] THP / swappiness / swap
[ ] 同机是否还有 noisy neighbor
[ ] 行情源/合约集合是否相同
```

→ Ch 3 [OS 背景](./chapter-03-操作系统.md) · Ch 11 [云](./chapter-11-云计算.md)

---

## 16.1.5–16.1.6 PMC 与软件事件

### 性能监控计数器（PMCs）

当 **宏观统计** 无法解释「为何 CPU 上更快」— 下钻 **微架构**：

```bash
perf stat -e cycles,instructions,cache-misses,LLC-load-misses,branch-misses -- ...
# IPC = instructions / cycles ↑ ？
```

| PMC 信号 | 可能含义 |
|----------|----------|
| **IPC ↑** | 更少 stall — cache/分支/调度改善 |
| **cache-miss ↓** | 数据布局、NUMA、邻居争用减少 |
| **branch-miss ↓** | 热路径分支更可预测 |
| cycles ↓ 且 instructions 同 | **真变少** vs 频率变化 |

**案例精神：** 用 **硬件计数量化** 「快了多少、像哪类快」— 再对齐软件假设。

→ Ch 6 [IPC / PMC](./chapter-06-中央处理器.md) · Ch 13 [`perf stat`](./chapter-13-perf性能分析.md)

### 软件事件（Software Events）

**交叉验证** PMC 现象的内核/运行时原因：

| 事件 | 工具 | 关联 |
|------|------|------|
| `context-switches` / `cpu-migrations` | `perf stat` | 调度、绑核 |
| `page-faults` / `major-faults` | `perf stat` | 内存、Swap |
| sched tracepoint | perf / BPF | 迁移、run queue |
| syscalls | `perf trace` / BPF | 路径变短？ |

**组合阅读：**

```
IPC ↑ + context-switches ↓  →  调度/绑核故事
IPC ↑ + cache-miss ↓        →  布局/邻居/cache 故事
IPC 同 + 吞吐 ↑              →  可能 workload 变或并行度变
```

→ Ch 7 [缺页](./chapter-07-内存.md) · Ch 5 [线程状态](./chapter-05-应用程序.md)

---

## 16.1.7–16.1.8 动态追踪与结论

### 动态追踪（Tracing）

统计与 PMC **仍不够** — 需要 **谁、哪条路径、何时**：

| 工具 | 案例中的角色 |
|------|--------------|
| **`perf record -g`** | CPU 热点是否迁移到其他函数 |
| **`perf trace` / BPF** | syscall 路径是否变短 |
| **Ftrace function_graph** | 内核路径耗时是否变 |
| **BCC / bpftrace** | runqlat、offcputime、tcpretrans 等 **专项** |

**原则（Ch 4）：**

- 追踪 **开销高** — 窄范围、短时长、带假设
- 要 **栈** — 否则只知「快了」，不知「哪条路径快了」

```bash
# 案例式组合（示意）
perf stat ...                    # 16.1.5–6
perf record -F 99 -g ...         # 16.1.7
sudo runqlat-bpfcc 10            # 调度是否仍饱和
sudo offcputime-bpfcc -p PID 20  # 阻塞栈是否消失
```

→ Ch 13–15 · [附录 C](./appendix-C-bpftrace单行命令.md)

### 结论（Conclusion）— Drill-Down 拼图

**案例收官：** 把线索 **串成因果链** — 能回答：

1. **什么** 变了（配置/负载/代码/环境）？
2. **哪一层** 受益（CPU cache / 调度 / 网络 / 磁盘）？
3. **证据** 是什么（PMC、trace、配置 diff）？
4. **可行动** 项 — 保留 win、写 runbook、还是 **其实是假象**？

**Unexplained Win 的典型结局类型（学习框架，非剧透具体 Netflix 细节）：**

| 类型 | 教训 |
|------|------|
| 负载/邻居变化 | 云/multi-tenant 对比必须 **同条件** |
| 配置 drift | 静态配置审计（16.1.4） |
| 缓存/预热 | 区分 cold vs steady state（Ch 12） |
| 真实代码/栈优化 | PMC + profile **可复现** |
| 测量 artifact | 指标口径、窗口、采样率 |

---

## 全书知识地图（本章如何串书）

```
┌─────────────────────────────────────────────────────────┐
│  Ch 16 Case Study · An Unexplained Win                  │
└─────────────────────────────────────────────────────────┘
         │
    Ch 2 方法论 ─── 问题陈述、假设、Drill-Down、反反面模式
         │
    Ch 4 工具地图 ── 先 stat/配置，再 perf/BPF
         │
    ┌────┴────┬────────┬────────┬────────┐
  Ch 6 CPU  Ch 7 Mem  Ch 8–9 I/O  Ch 10 Net  Ch 11 Cloud
    └────┬────┴────────┴────────┴────────┘
         │
    Ch 12 基准 ─── 对比是否公平、WSS、Sanity Check
         │
    Ch 13 perf ─── stat PMC + record 火焰图
    Ch 14 Ftrace ─ graph / hwlat（若需要）
    Ch 15 BPF ─── runqlat、offcputime、tcpretrans…
         │
    附录 A USE ─── 各资源 U/S/E 核对
    附录 C bpftrace ─ ad hoc 收尾
```

---

## 推荐阅读顺序（Gregg + 本仓库）

| 读者 | 顺序 |
|------|------|
| **新手** | **先 Ch 16 预览** → Ch 1–2 → Ch 4 → 资源章 → Ch 13–15 → **再读 Ch 16** |
| **HFT 已有基础** | Ch 1–15 按 OUTLINE → **Ch 16 作总复盘** → 附录 A/C |
| **之后** | [03-BPF 专书](../03-BPF-Performance-Tools/) · [11-HFT 工程](../11-HFT-Low-Latency-Practice/) |

---

## HFT 版「Unexplained Win」演练模板

**场景：** 部署后 tick P99 从 8 µs → 5 µs，团队不确定该不该庆祝。

| 步骤 | 动作 |
|------|------|
| 1 陈述 | 同一合约集、同一时段、同一机器角色？ |
| 2 统计 | `mpstat`、`pidstat`、`ss`、**邻居是否变化** |
| 3 配置 diff | 内核、绑核、THP、DPDK 参数、策略 binary |
| 4 PMC | `perf stat` IPC、cache-miss、context-switches |
| 5 Profile | `perf record` 热点是否迁移 |
| 6 BPF | `runqlat`、`offcputime`、行情路径 syscall |
| 7 结论 | 写入 **release note** — 可复现的 win 还是环境 noise |

→ [11-HFT ch10 延迟测量](../11-HFT-Low-Latency-Practice/chapter-10-延迟测量与基准压测.md)

---

## 本章 Checklist

- [ ] 理解 **Unexplained Win** 为何值得查
- [ ] 能写出 **问题陈述 + 2–3 假设 + 验证顺序**
- [ ] 排查顺序：**统计 → 配置 → PMC → trace**
- [ ] 能把案例每一步 **映射到本仓库章节号**
- [ ] （可选）新手 **先读本章** 再读全书；二刷对照工具名

---

## Gregg 本章金句（HFT 版）

> 第十六章是 **全书演习** — 不是教新公式，是教 **在真实云生产里如何把公式用一遍**。  
> **「莫名变快」和「莫名变慢」一样，都是性能工程师的功课** — 不懂赢，就不懂输。

---

## 相关章节

- 上一章：[chapter-15-BPF技术.md](./chapter-15-BPF技术.md)
- 下一章：[appendix-A-USE方法Linux.md](./appendix-A-USE方法Linux.md)
- 方法论：[chapter-02-方法论.md](./chapter-02-方法论.md)
- 观测入门：[chapter-01-简介.md](./chapter-01-简介.md) · [chapter-04-观测工具.md](./chapter-04-观测工具.md)
- 资源专章：Ch [6](./chapter-06-中央处理器.md)–[11](./chapter-11-云计算.md)
- 工具专章：Ch [13](./chapter-13-perf性能分析.md)–[15](./chapter-15-BPF技术.md)
- BPF 专书：[03-BPF-Performance-Tools](../03-BPF-Performance-Tools/)
- HFT 压测：[11-HFT ch10](../11-HFT-Low-Latency-Practice/chapter-10-延迟测量与基准压测.md)
- 全书目录：[OUTLINE.md](./OUTLINE.md)
