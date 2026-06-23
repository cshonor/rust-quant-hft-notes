# 07 · 系统底层动手（自制 OS / CPU）

**文件夹 `07`** · [LEARNING-CHAIN](../LEARNING-CHAIN.md)

> **定位：** **知其所以然 → 动手造** — 用最小系统把进程、中断、内存映射、指令执行「摸一遍」。  
> **前置：** `01` CSAPP 地基 + `05` LKD / `06` Gorman（概念）  
> **执行顺序：** `06` Gorman → **`07` 本模块** → `08` PNP → `09` UNP → `10`–`12` 网络纵深 → `13` HFT

## 学习链位置

```
06 Gorman
    ↓
07 自制 OS / CPU（本文件夹）     ← 系统底层动手
    ↓
08 陈硕 PNP / muduo              ← C++ 网络实战
    ↓
09 UNP → 10 TCP/IP → 11 Rosen → 12 DPDK
    ↓
13 HFT Practice · 14 Rust
```

## 子模块

| 子文件夹 | 内容 | 一句话 |
|----------|------|--------|
| [07-1-30days-os](./07-1-30days-os/) | 《30 天自制操作系统》动手笔记 | 引导扇区 → 保护模式 → 进程/中断/内存 |
| [07-2-30days-cpu](./07-2-30days-cpu/) | 《30 天自制 CPU》动手笔记 | 从门电路到汇编器 — 理解指令如何被 CPU 执行 |

## HFT 为什么要读

| 自制 OS | 自制 CPU | 对 HFT 的价值 |
|---------|----------|---------------|
| 中断、上下文切换、页表 | 取指译码执行、流水线直觉 | 理解绑核、syscall、缺页 **在硬件上是什么** |
| 无标准库的最小运行时 | 指令级时序 | 读 `perf`、cache 类比时不停留在背参数 |

## 交叉阅读

- 概念铺垫：[05-LKD](../05-Linux-Kernel-Development/) · [06-Gorman](../06-Linux-Virtual-Memory-Manager/) · [01-CSAPP](../01-CSAPP-3rd/)
- **下一步网络：** [08-Practical-Network-Programming](../08-Practical-Network-Programming/)
- 工程落地：[13-HFT-Low-Latency-Practice](../13-HFT-Low-Latency-Practice/)
