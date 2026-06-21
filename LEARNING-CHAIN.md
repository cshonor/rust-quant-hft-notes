# HFT 学习链路 · 从知其所以然到动手实现

> **链路编号（L1–L5）≠ 文件夹编号（`00`–`12`）。** 文件夹序号仅作仓库归类；**复习、分享、带人入门请跟本文链路走。**

整条路径的设计意图：

```
知其所以然  →  知其然  →  工具落地  →  系统纵深  →  动手实现
   L1           L2          L3          L4           L5
```

---

## 一眼版 · 核心进阶路径

```
L0  业务锚点          00-Harris（LOB / 市场结构）
         ↓
L1  知其所以然        08-CSAPP（+ 07-Hennessy Ch2 配套）
    程序如何在硬件上跑：Cache / 进程 / VM / 锁
         ↓
L2  知其然            01-Systems-Performance-2nd
    性能分析通用语言：USE / 延迟分解 / perf / 观测选型
         ↓
L3  工具落地          09-BPF-Performance-Tools
    进阶追踪：bpftrace / BCC / 生产排抖动（紧接 L2）
         ↓
L4  系统纵深          02-LKD → 03-Gorman → 04/05/06/12 网络栈
    绑核 / 中断 / NUMA / 协议→Socket→内核→DPDK（写引擎与调优的素材）
         ↓
L5  动手实现          10-HFT-Practice（C++ 工程） + 11-Rust-Quant-Guide
    整机调优、订单簿、无锁、发单路径 — 把 L1–L4 落到代码
```

**最短分享版（四步）：** CSAPP → SysPerf → BPF → HFT/Rust 实战

---

## 链路 ↔ 文件夹对照

| 链路 | 阶段 | 文件夹 | 你要带走什么 |
|------|------|--------|--------------|
| **L0** | 业务锚点 | `00` Harris | LOB、撮合、订单类型 — 写引擎的业务语言 |
| **L1** | 知其所以然 | `08` CSAPP · `07` Hennessy Ch2 | 火焰图里为何是这个函数；锁/cache miss 的硬件原因 |
| **L2** | 知其然 | `01` SysPerf | 怎么量、怎么选工具、USE/RED、危机工具包 |
| **L3** | 工具落地 | `09` BPF Tools | 现场 bpftrace 单行、按 CPU/网络/内存查抖动 |
| **L4** | 系统纵深 | `02` `03` `04`–`06` `12` | 绑核/isolcpus、THP、收包路径、DPDK 旁路 |
| **L5** | 动手实现 | `10` HFT · `11` Rust | 共置调优、引擎架构、Rust 量化工程 |

> Gregg 两本书在链路上是 **L2 → L3 连续阅读**，不必等 L4 结束。

---

## 各步给下一步的铺垫

| 从 | 到 | 铺垫关系 |
|----|-----|----------|
| **L1 CSAPP** | **L2 SysPerf** | 看懂火焰图栈、理解 off-CPU 是 syscall/锁/缺页，而非背 USE 口诀 |
| **L2 SysPerf** | **L3 BPF** | Ch 4 观测分类、Ch 15 BPF 预览 → 全书 bpftrace/BCC 展开 |
| **L3 BPF** | **L4 内核/网络** | 用 eBPF 验证绑核、软中断、run queue；读 LKD/Rosen 时有「量」的抓手 |
| **L1–L4** | **L5 10/11** | CSAPP 布局订单簿 + SysPerf 量延迟 + BPF 查尖刺 + LKD/DPDK 调路径 → 写 C++/Rust 热路径 |

---

## L1 CSAPP · 地基篇读什么

配合 [07-Hennessy Ch2](./07-Computer-Architecture-6th/)（MESI / 伪共享理论）：

```
Ch1 概览（可选）→ Ch4–6 CPU/优化/Cache
→ Ch8 进程/syscall → Ch9 虚拟内存 → Ch12 并发与锁
```

网络章 **Ch10–11** 留到 **L4 网络栈** 与 UNP/Rosen 一起读。

→ 笔记：[08-CSAPP-3rd/](./08-CSAPP-3rd/)

---

## L2 → L3 · Gregg 双书

| L2 `01-SysPerf` | L3 `09-BPF` |
|-----------------|-------------|
| 方法论、工具地图、perf 火焰图 | bpftrace/BCC 生产脚本 |
| Ch 13 perf · Ch 15 BPF 概念 | Part I–II 按子系统查抖动 + XDP note |

→ [01 笔记](./01-Systems-Performance-2nd/) · [09 笔记](./09-BPF-Performance-Tools/)

---

## L5 工程实践 · 10 与 11 怎么选

| | `10` HFT Low-Latency Practice | `11` Rust Quant Guide |
|---|------------------------------|------------------------|
| **语言** | C++ 案例为主 | Rust 全栈量化 |
| **侧重** | 共置调优、交易所对接、压测、整机架构 | 订单簿、无锁、Tokio/io_uring |
| **读法** | L3 后可直接切入；网络章与 L4 交叉 | 与 L5 并行或 L4 后精读 |

二者 **互补**，不是二选一；见 [10↔参考书映射](./READING-LIST.md#与-10-hft-low-latency-practice-章节映射)。

---

## 与完整路线图的关系

- **本文（LEARNING-CHAIN）** — 分享/复习用的 **一条主叙事**
- **[HFT-READING-ROADMAP.md](./HFT-READING-ROADMAP.md)** — 含外部书目、小节级 🔴/🟡/⚪、不漏项检查清单
- **[READING-LIST.md](./READING-LIST.md)** — 八本书章节裁剪表
- **[CROSS-MODULE-GUIDE.md](./CROSS-MODULE-GUIDE.md)** — DPDK↔UNP↔CSAPP 技术对照

**推荐执行序号：**

```
L0 → L1(⑤⑥) → L2(①) → L3(⑧) → L4(②③外A外B④⑥⑫) → L5(⑩⑪)
```

（括号内为 ROADMAP 书目编号，与文件夹编号不同。）
