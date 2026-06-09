# Systems Performance 2nd — Brendan Gregg

**文件夹 01 · 原书目第 1 册** · [返回总清单](../READING-LIST.md#1-systems-performance-enterprise-and-the-cloud-2nd--brendan-gregg)

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
| Ch 1–2 方法论、观测基础 | [chapter-01-方法论与观测基础.md](./chapter-01-方法论与观测基础.md) |
| Ch 6 CPU | [chapter-02-CPU调度与NUMA.md](./chapter-02-CPU调度与NUMA.md) |
| Ch 7 Memory | [chapter-03-内存与TLB.md](./chapter-03-内存与TLB.md) |
| Ch 10 Networks | [chapter-04-网络与网卡调优.md](./chapter-04-网络与网卡调优.md) |

## 选读

| 原书章节 | 笔记文件 |
|----------|----------|
| Ch 11 Protocols（TCP/UDP） | [chapter-05-协议栈TCP与UDP.md](./chapter-05-协议栈TCP与UDP.md) |
| Ch 12+ Benchmarking 泛化 | 无单独笔记，压测方法论可借鉴 |

## 跳过（无笔记文件）

- Ch 8 File Systems / Ch 9 Disks — 除非做持久化日志/审计
- Ch 12+ Cloud 章节

## HFT 产出

建立「延迟从哪来 → 怎么量 → 怎么调」的总框架。
