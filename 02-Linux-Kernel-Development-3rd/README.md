# Linux Kernel Development 3rd — Robert Love

**文件夹 02 · 原书目第 2 册** · [返回总清单](../READING-LIST.md#2-linux-kernel-development-3rd--robert-love)

## 本书 HFT 读法

| 标签 | 含义 |
|------|------|
| **必读** | 本文件夹有笔记 · 精读，HFT 主线建议认真读 |
| **选读** | 本文件夹有笔记 · 选读，有余力再读 |
| **跳过** | 本文件夹无笔记，当前 HFT 目标下默认不读 |

> 有 `.md` 的章节 = 建议做笔记；没建文件的章节 = 默认跳过（有特殊需求再读）。

## 必读（精读）

| 原书章节 | 笔记文件 |
|----------|----------|
| Ch 4 Process Scheduling | [chapter-02-进程调度.md](./chapter-02-进程调度.md) |
| Ch 7 Interrupts and Bottom Halves | [chapter-03-中断与下半部.md](./chapter-03-中断与下半部.md) |
| Ch 8 Deferred Work | [chapter-04-延迟工作与软中断.md](./chapter-04-延迟工作与软中断.md) |
| Ch 9 Kernel Synchronization | [chapter-05-内核同步原语.md](./chapter-05-内核同步原语.md) |
| Ch 10 Timers and Time Management | [chapter-06-定时器与时间.md](./chapter-06-定时器与时间.md) |

## 选读

| 原书章节 | 笔记文件 |
|----------|----------|
| Ch 3 Process Management | [chapter-01-进程管理.md](./chapter-01-进程管理.md) |
| Ch 11 Memory Management（概述） | [chapter-07-内存管理概述.md](./chapter-07-内存管理概述.md) |

## 跳过（无笔记文件）

- Ch 2 Getting Started / Ch 20 Patch
- Ch 12–18 VFS / Block / Page Cache — 交易热路径不走磁盘

## HFT 产出

理解「绑核、隔离、中断」在内核里怎么实现。
