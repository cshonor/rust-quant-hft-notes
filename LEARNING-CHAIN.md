# HFT 学习链路 · 从知其所以然到动手实现

> **文件夹 `00`–`14`。** **执行序号**见文末 — 网络段核心：`07` → `08` PNP → `09` UNP → `10`–`12` 纵深。

整条路径的设计意图：

```
知其所以然  →  知其然  →  工具落地  →  系统纵深  →  底层+网络实战  →  工程实现
  01–04         02          03          05–06         07–12                 13–14
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

07  自制 OS / CPU         系统底层动手（07-1 / 07-2）
08  陈硕 PNP / muduo      C++ 网络实战 — 先写服务骨架
09  UNP                   Socket API 系统化（对照 08 实验）
01  CSAPP Ch10–11         网络篇（与 08/09 合读）
10  TCP/IP 卷一           协议语义
11  Rosen                 内核网络栈
12  DPDK                  用户态旁路 · 网络闭环

13  HFT Practice          动手实现 · C++ 低延迟工程
14  Rust Quant Guide      动手实现 · Rust 量化
```

**最短四步：** `01` CSAPP → `02` SysPerf → `03` BPF → `13`/`14` 实战

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
| **07** | [自制 OS/CPU](./07-system-low-level-hands-on/) | 底层动手 | 中断、页表、指令 |
| **08** | [PNP / muduo](./08-Practical-Network-Programming/) | 网络实战 | epoll、粘包、Reactor 骨架 |
| **09–12** | UNP / TCP/IP / Rosen / DPDK | 网络纵深 | API → 协议 → 内核 → 旁路 |
| **13** | HFT Practice | 动手实现 | C++ 整机工程 |
| **14** | Rust Guide | 动手实现 | Rust 量化工程 |

---

## 各步铺垫

| 从 | 到 | 关系 |
|----|-----|------|
| **07 自制系统** | **08 PNP** | 摸过中断/进程，写网络服务不懵 |
| **08 PNP** | **09 UNP** | 先写过 epoll 骨架，再啃 Stevens API |
| **09 UNP** | **10 TCP/IP** | 知道 socket 底下协议字段什么意思 |
| **10–12** | **13 HFT** | 网络全链路落地到交易系统 |

---

## 08 · 陈硕 PNP / muduo

| 外部入口 | 说明 |
|----------|------|
| [PNP/](https://github.com/cshonor/Computer-Networking/tree/main/PNP) | 实验大纲、study.md、code/ |
| [本仓库索引](./08-Practical-Network-Programming/) | HFT 裁剪与交叉阅读 |

→ 下一步：[09-UNP-Vol1](./09-UNP-Vol1/)

---

## 12 DPDK · 实体书与时机

**不要过早。** 先完成 `08`–`11` 标准网络路径，且 **perf 已定位网络收发是瓶颈** 再读。

→ [note-DPDK实体书递进](./12-DPDK-Low-Latency-Network/01-Intro-Book/notes/note-DPDK实体书递进.md)

---

## 13 与 14

| | 13 HFT Practice | 14 Rust Guide |
|---|-----------------|---------------|
| 语言 | C++ 为主 | Rust |
| 侧重 | 共置、对接、压测、架构 | 订单簿、无锁、工程栈 |

→ [READING-LIST · 与 13 映射](./READING-LIST.md#与-13-hft-low-latency-practice-章节映射)

---

## 相关文档

- [HFT-READING-ROADMAP.md](./HFT-READING-ROADMAP.md) — 小节级 🔴/🟡/⚪
- [READING-LIST.md](./READING-LIST.md) — 章节裁剪
- [CROSS-MODULE-GUIDE.md](./CROSS-MODULE-GUIDE.md) — 技术对照

**执行序号：** `00 → 01(+04) → 02 → 03 → 05 → 06 → 07 → 08 → 09 → 01网络章 → 10 → 11 → 12 → 13 → 14`
