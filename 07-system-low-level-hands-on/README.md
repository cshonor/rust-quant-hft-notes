# 07 · 系统底层动手（自制 OS / CPU）

**文件夹 `07`** · 接在网络协议栈之后、HFT 专项之前 · [LEARNING-CHAIN](../LEARNING-CHAIN.md)

> **定位：** **知其所以然 → 动手造** — 用最小系统把进程、中断、内存映射、指令执行「摸一遍」，再读 `12-HFT` 时不把内核当黑盒。  
> **前置：** `01` CSAPP 地基 + `05` LKD / `06` Gorman（概念）；**建议与 `08`–`11` 网络栈合读或紧随其后**。  
> **执行顺序：** `06` Gorman → `08`–`11` 网络 → **`07` 本模块** → `12` HFT → `13` Rust

## 学习链位置

```
08 TCP/IP → 09 UNP → 10 Rosen → 11 DPDK     ← 网络协议栈
        ↓
07 自制 OS / CPU（本文件夹）                  ← 系统底层动手
        ↓
12 HFT Practice · 13 Rust Guide              ← 高频交易工程
```

> **说明：** 资源管理器里 `07` 排在 `08` 网络之前，是 **文件夹序号**；**推荐阅读顺序** 见上 — 先走通网络，再动手造系统，最后进 HFT。

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
| 裸机 I/O | 总线与存储层次 | 与 `11-DPDK` 用户态旁路形成对照 |

## 交叉阅读

- 概念铺垫：[05-LKD](../05-Linux-Kernel-Development/) · [06-Gorman](../06-Linux-Virtual-Memory-Manager/) · [01-CSAPP](../01-CSAPP-3rd/)
- 性能方法论：[02-SysPerf](../02-Systems-Performance-2nd/)
- 网络（建议先读）：[08-TCP-IP](../08-TCP-IP-Illustrated-Vol1/) → [11-DPDK](../11-DPDK-Low-Latency-Network/)
- 工程落地：[12-HFT-Low-Latency-Practice](../12-HFT-Low-Latency-Practice/)
