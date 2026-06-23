# HFT 学习链路 · 从知其所以然到动手实现

> **文件夹 `00`–`13`。** 资源管理器按名称排序 ≠ 全部推荐顺序 — **执行序号**见文末。

整条路径的设计意图：

```
知其所以然  →  知其然  →  工具落地  →  系统纵深  →  底层动手  →  动手实现
  01–04         02          03          05–06         07            12–13
                              网络纵深 08–11 插在 07 之前读
```

---

## 一眼版 · 推荐执行顺序

```
00  Harris              业务锚点（LOB / 市场结构）
01  CSAPP                知其所以然 — Cache / 进程 / VM / 锁
04  Hennessy Ch2          配套 01（MESI / 伪共享，可与 01 交叉）
02  SysPerf               知其然 — USE / 延迟分解 / perf
03  BPF                   工具落地 — bpftrace/BCC（紧接 02）
05  LKD                   内核 · 绑核 / 中断 / 调度
06  Gorman                虚拟内存 · NUMA / TLB / THP

08  TCP/IP 卷一           协议（外部笔记仓库）
09  UNP                   Socket API（外部笔记仓库）
01  CSAPP Ch10–11         网络篇（与 09/10 合读）
10  Rosen                 内核网络栈
11  DPDK                  用户态旁路 · 网络闭环

07  自制 OS / CPU         系统底层动手（07-1 / 07-2）
12  HFT Practice          动手实现 · C++ 低延迟工程
13  Rust Quant Guide      动手实现 · Rust 量化
```

**最短四步：** `01` CSAPP → `02` SysPerf → `03` BPF → `12`/`13` 实战

---

## 文件夹 ↔ 阶段

| 文件夹 | 书 / 模块 | 阶段 | 一句话 |
|--------|-----------|------|--------|
| **00** | Harris | 业务 | LOB、撮合、订单类型 |
| **01** | CSAPP | 知其所以然 | 程序如何在硬件上跑 |
| **02** | SysPerf | 知其然 | 怎么量、USE/RED、观测选型 |
| **03** | BPF Tools | 工具落地 | 生产 bpftrace / BCC |
| **04** | Hennessy | 理论配套 | Cache/MESI/一致性（配 01） |
| **05** | LKD | 系统纵深 | 调度、中断、绑核 |
| **06** | Gorman | 系统纵深 | 内核视角虚拟内存 |
| **08–11** | 网络栈 | 系统纵深 | 协议→Socket→内核→DPDK |
| **07** | [自制 OS/CPU](./07-system-low-level-hands-on/) | 底层动手 | 网络之后、HFT 之前 |
| **12** | HFT Practice | 动手实现 | C++ 整机工程 |
| **13** | Rust Guide | 动手实现 | Rust 量化工程 |

---

## 各步铺垫

| 从 | 到 | 关系 |
|----|-----|------|
| **01 CSAPP** | **02 SysPerf** | 看懂火焰图、理解 off-CPU，而非背 USE |
| **02 SysPerf** | **03 BPF** | Ch15 预览 → bpftrace/BCC 全书 |
| **03 BPF** | **05–11** | 用 eBPF 验证绑核、软中断、网络路径 |
| **08–11 网络** | **07 自制系统** | 协议栈走通后，动手摸中断/页表/指令 |
| **07 + 01–11** | **12–13** | 知识落到 C++/Rust 热路径代码 |

---

## 01 CSAPP · 分两遍

**第一遍（02 SysPerf 之前）：** Ch1 → Ch4–6 → Ch8 → Ch9 → Ch12  
**第二遍（09/10 网络阶段）：** Ch10–11  
**04 Hennessy Ch2** 与 Ch6 交叉读。

→ [01-CSAPP-3rd/](./01-CSAPP-3rd/)

---

## 02 → 03 · Gregg 双书

| 02 SysPerf | 03 BPF |
|------------|--------|
| 方法论、工具地图、perf | bpftrace/BCC 生产脚本 |
| Ch13 perf · Ch15 BPF 概念 | Part I–II + XDP note |

→ [02 笔记](./02-Systems-Performance-2nd/) · [03 笔记](./03-BPF-Performance-Tools/)

---

## 11 DPDK · 实体书与时机

**不要过早。** 先完成 `01` CSAPP、`02` SysPerf，走通 `08`→`10` 内核网络路径，且 **perf 已定位网络收发是瓶颈** 再读。

| 顺序 | 实体书 | 作用 |
|------|--------|------|
| ① | 《深入浅出 DPDK》 | 旁路内核栈、用户态接管网卡 |
| ② | 《Linux 高性能网络详解》 | DPDK + RDMA + XDP；方案选型 |

→ [note-DPDK实体书递进](./11-DPDK-Low-Latency-Network/01-Intro-Book/notes/note-DPDK实体书递进.md)

---

## 07 · 自制 OS / CPU

| 子模块 | 内容 |
|--------|------|
| [07-1-30days-os](./07-system-low-level-hands-on/07-1-30days-os/) | 最小 OS：中断、多任务、页表 |
| [07-2-30days-cpu](./07-system-low-level-hands-on/07-2-30days-cpu/) | 最小 CPU：指令与数据通路 |

**建议：** `08`–`11` 网络读完后进入 `07`，再开 `12` HFT。

---

## 12 与 13

| | 12 HFT Practice | 13 Rust Guide |
|---|-----------------|---------------|
| 语言 | C++ 为主 | Rust |
| 侧重 | 共置、对接、压测、架构 | 订单簿、无锁、工程栈 |

→ [READING-LIST · 与 12 映射](./READING-LIST.md#与-12-hft-low-latency-practice-章节映射)

---

## 相关文档

- [HFT-READING-ROADMAP.md](./HFT-READING-ROADMAP.md) — 小节级 🔴/🟡/⚪
- [READING-LIST.md](./READING-LIST.md) — 章节裁剪
- [CROSS-MODULE-GUIDE.md](./CROSS-MODULE-GUIDE.md) — 技术对照

**执行序号：** `00 → 01(+04) → 02 → 03 → 05 → 06 → 08 → 09 → 01网络章 → 10 → 11 → 07 → 12 → 13`
