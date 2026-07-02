# HFT 学习链路 · 从知其所以然到动手实现

> **文件夹 `00`–`16` = 物理编号（路径不变）；「执行顺序」以本文为准。**  
> **2025-06 调整：** `03` SysPerf、`04` BPF **后置**（有内核/网络/系统可观测后再读）；`09/01` MikanOS 在 `09/02` 30 天之前。

```
知其所以然 → 系统纵深 → 底层动手 → 网络 → 性能观测 → 工程
  01–02        05–08       09         10–14    03–04      15–16
```

---

## 一眼版 · 执行顺序

```
00  Harris
01  CSAPP
02  Hennessy

05  LKD → 06 ULK → 07 Gorman → 08 TLPI

09  自制 OS / CPU
    └─ 01-mikan-os（HFT 主线）· 02-30days-os（可选启蒙）

17  C++ · [cpp-learning-notes](https://github.com/cshonor/cpp-learning-notes)
10  陈硕 PNP / muduo
11  UNP
01  CSAPP Ch10–11（网络篇，可与 10–11 交叉）
12  TCP/IP → 13  Rosen → 14  DPDK

03  SysPerf → 04  BPF          ← 后置：有东西可 profile 再开

15  HFT Practice
16  Rust Guide

── 可选 · 嵌入式 Linux 支线（18 起，建议 05–08 后）──
18  ARM64 → 19  U-Boot/内核 → 20  驱动 → 21  DT → 22  实战 → 23  PID/飞控
```

**HFT 最短路径（当前）：** `01` CSAPP → `02` Hennessy → `05`–`08` 内核/TLPI → `09/01` MikanOS → `14` DPDK → `03`–`04` 观测 → `15` HFT

**嵌入式支线：** `18 → … → 23`（与 HFT **并行或后置**）

---

## 为何这样排？

| 调整 | 理由 |
|------|------|
| **`02` Hennessy 紧接 `01` CSAPP** | 机器级程序 → 体系结构 → 再读内核 |
| **`03`/`04` 后置到网络/DPDK 之后** | 性能方法论需要 **可观测的真实系统**；先懂内核/网络再开 Gregg 双书 |
| **`09/01` MikanOS 在 `09/02` 30 天前** | HFT 走现代 UEFI/64 位；30 天 BIOS 启蒙可选 |
| **`06` ULK 紧接 `05` LKD** | 内核地图 → 立刻下潜源码 |

---

## 文件夹 ↔ 阶段

| 文件夹 | 模块 | 执行阶段 |
|--------|------|----------|
| **03** | [SysPerf](./03-Systems-Performance-2nd/) | **后置** · 14 之后或 15 之前 |
| **04** | [BPF Tools](./04-BPF-Performance-Tools/) | **紧接 03** |
| **08** | [TLPI](./08-The-Linux-Programming-Interface/) | Linux 用户态 syscall |
| **09/01** | [MikanOS](./09-system-low-level-hands-on/01-mikan-os/) | HFT OS 动手主线 |
| **09/02** | [30 天 OS](./09-system-low-level-hands-on/02-30days-os/) | 可选启蒙 |
| **10–14** | PNP / UNP / TCP/IP / Rosen / DPDK | 网络纵深 |
| **15–16** | HFT / Rust | 工程实现 |

---

## 内核段衔接

```
05 LKD（内核里有什么）
    ↓
06 ULK（代码里长什么样）
    ↓
07 Gorman（VM 深度）
    ↓
08 TLPI（用户态 epoll/mmap）
    ↓
09/01 MikanOS（UEFI/64 位 · 从零搭机制）
    ↓
10–14 网络栈
    ↓
03 SysPerf → 04 BPF（观测与 eBPF 落地）
    ↓
15 HFT
```

→ [09 HFT 学习主次](./09-system-low-level-hands-on/HFT-AND-EMBEDDED-PRIORITY.md) · [08 TLPI OUTLINE](./08-The-Linux-Programming-Interface/OUTLINE.md)

---

## 相关文档

- [READING-LIST.md](./READING-LIST.md) · [HFT-READING-ROADMAP.md](./HFT-READING-ROADMAP.md) · [CROSS-MODULE-GUIDE.md](./CROSS-MODULE-GUIDE.md)

**HFT 主线执行序号：** `00 → 01 → 02 → 05 → 06 → 07 → 08 → 09/01 → 17 → 10 → 11 → 01网络 → 12 → 13 → 14 → 03 → 04 → 15 → 16`

> **C++ 外部仓：** [17-cpp-learning-notes/](./17-cpp-learning-notes/) — **09 之后、10 PNP 之前** 至少读完 *Effective Modern C++*。
