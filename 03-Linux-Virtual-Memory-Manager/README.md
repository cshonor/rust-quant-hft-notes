# Understanding the Linux Virtual Memory Manager — Mel Gorman

**文件夹 03 · 原书目第 3 册** · [返回总清单](../READING-LIST.md#3-understanding-the-linux-virtual-memory-manager--mel-gorman)

## 本书 HFT 读法

| 标签 | 含义 |
|------|------|
| **必读** | 本文件夹有笔记 · 精读，HFT 主线建议认真读 |
| **选读** | 本文件夹有笔记 · 选读，有余力再读 |
| **跳过** | 本文件夹无笔记，当前 HFT 目标下默认不读 |

> 有 `.md` 的章节 = 建议做笔记；没建文件的章节 = 默认跳过（有特殊需求再读）。

## 必读（精读）

| 主题 | 笔记文件 |
|------|----------|
| 物理内存 / Zones / NUMA | [chapter-01-物理内存与NUMA.md](./chapter-01-物理内存与NUMA.md) |
| Page Tables / TLB | [chapter-02-页表与TLB.md](./chapter-02-页表与TLB.md) |
| Slab / Slub 分配器 | [chapter-03-Slab分配器.md](./chapter-03-Slab分配器.md) |
| Transparent Huge Pages (THP) | [chapter-04-透明大页THP.md](./chapter-04-透明大页THP.md) |

## 选读

| 主题 | 笔记文件 |
|------|----------|
| Page Fault / Reclaim（核心部分） | [chapter-05-缺页与回收.md](./chapter-05-缺页与回收.md) |

## 跳过（无笔记文件）

- Swap / OOM 深读 — HFT 机器通常禁用 swap
- File-backed / Writeback — 除非做持久化

## HFT 产出

订单簿/内存池布局、NUMA 绑内存、伪共享（配合 Hennessy Ch2）的理论依据。
