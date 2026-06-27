# Ch 6 物理页分配 · Physical Page Allocation

> **Understanding the Linux Virtual Memory Manager** · Mel Gorman · **选读**（HFT：**NUMA 本地页、GFP、per-CPU pageset、zone 水位** 与延迟/抖动强相关 — 建议至少精读 §2、§4、§6）

本章讲 Linux **运行时** 如何 **分配 / 释放物理页框** — 核心算法是 **二进制伙伴分配器 (Binary Buddy Allocator)**：**2 的幂次连续页块** + **拆分 / 合并**，追求 **极高分配速度**。

> **源码入口：** [`mm/page_alloc.c`](https://elixir.bootlin.com/linux/latest/source/mm/page_alloc.c)（Ch 1 阅读路线第 3 步）· 接 [Ch 5](./chapter-05-启动内存分配器.md) **`mem_init()` 移交** 的空闲页。

---

## 本章在 VM 子系统中的位置

```
Ch 5 bootmem/memblock 退役 ──►  Buddy 接管 zone freelist
        ↓
Ch 6 alloc_pages / free_pages   ← 本章
        ↓
Ch 4 缺页 fault ──► 最终也调用 page allocator 拿 struct page
Ch 8 slab ──► 从 Buddy 拿整页再切小对象
Ch 7 vmalloc ──► 需要连续物理页时仍依赖 Buddy（或 CMA 等）
```

**HFT：** 用户态 **`mmap` fault**、内核 **`kmalloc`**（经 slab）底层都可能走到 **`alloc_pages`**；**`GFP_ATOMIC`**、**direct reclaim**、**跨 node 分配** 都会表现为 **延迟尖刺**。

→ 交叉：[Ch 2 Zone 水位](./chapter-02-描述物理内存.md#区域水位线-zone-watermarks) · [Ch 4 缺页](./chapter-04-进程地址空间.md#4-异常处理与缺页异常-page-faulting)

---

## 1. 空闲块的管理 (Managing Free Blocks)

### 阶 (Order)

物理内存按 **连续页框块** 组织，块大小为 **2 的幂次页**：

| Order | 块含页数 |
|-------|----------|
| 0 | 1 页 |
| 1 | 2 页 |
| 2 | 4 页 |
| … | … |
| 9 | 512 页（原书 **`MAX_ORDER=10`** 时，最大 order 索引为 9） |

**阶 (order)** = 该块 **log₂(页数)** 的指数（表述上：order `k` 块含 **2^k** 页）。

### 数据结构

每个 **Zone** 维护 **`free_area_t` 数组**（现代 **`struct free_area`**）— **每个 order 一条空闲块链表**：

```
zone->free_area[0]  ──►  1-page  free blocks
zone->free_area[1]  ──►  2-page  free blocks
        …
zone->free_area[MAX_ORDER-1]  ──►  最大块
```

### 伙伴位图 (Buddy Bitmap)

为 **省空间**，用 **1 bit** 表示 **一对伙伴块** 的状态：

| 位值 | 含义（原书） |
|------|--------------|
| **0** | 该 **伙伴对** 要么 **全空闲**，要么 **全占用** |
| **1** | **恰有一边** 被占用 |

合并 / 拆分时查位图，决定 **能否 coalesce** 成更高 order。

→ 与 Ch 2 **`struct zone`**、**`pageset`** 同在一个 zone 数据结构族中。

---

## 2. 页面分配 (Allocating Pages)

### 核心：`alloc_pages()` / `__alloc_pages()`

**分配 order = n** 的连续 **2^n** 页：

```
请求 order-k 块
    free_area[k] 有空？ ──是──► 取下返回
         │
         否
         ▼
    从更高 order 取块 ──► **拆分 (split)**
         │                    ├─ 一半用于本次分配
         │                    └─ 另一半（伙伴）挂入较低 order 链表
         ▼
    重复直到满足或失败
```

**按需拆分 (Splitting)：** 没有正好大小的块时，**把大块一分为二**，一半分配、一半 **降级** 入链 — Buddy 算法核心。

### 节点本地与 Zone Fallback

| 策略 | 行为 |
|------|------|
| **Node-local** | 优先从 **当前 CPU 所属 NUMA node** 分配 |
| **Zone fallback** | 首选 zone（如 **HIGHMEM**）不够 → 按预定顺序 **降级**（如 **NORMAL → DMA**） |

**HFT：** **`numactl --membind`**、**`mbind(MPOL_BIND)`** 是在 **用户态约束** 这一策略；违背后 **remote node** 分配 = **更高延迟**。

→ [Ch 2 Nodes](./chapter-02-描述物理内存.md#1-内存节点-nodes)

---

## 3. 页面释放 (Free Pages)

### `free_pages()` 与合并 (Coalescing)

释放 **order-k** 块时：

```
free 块 B
    伙伴 B' 也空闲？ ──否──► B 挂入 free_area[k]
         │
         是
         ▼
    合并为 order-(k+1) 块 ──► 递归检查能否继续合并
```

**与拆分对称** — 保证 **相同 order 的空闲块可拼接**，缓解 **外部碎片**。

---

## 4. GFP 标志与进程标志 (GFP & Process Flags)

### GFP (Get Free Pages)

调用 **`alloc_pages(gfp_mask, order)`** 时必须传 **`gfp_mask`** — 声明 **允许分配器做什么 / 不能做什么**：

| 标志（示例） | 含义 | 典型场景 |
|--------------|------|----------|
| **`GFP_KERNEL`** | 可 **睡眠** 等待页、可触发 **直接回收** | 进程上下文、多数内核路径 |
| **`GFP_ATOMIC`** | **不可睡眠** — 失败则立即返回 | **中断 / spinlock 持有** 中分配 |
| **`GFP_NOIO`** | 回收路径中 **不发起 I/O** | 避免 **存储栈重入死锁** |
| **`GFP_HIGHUSER` / `GFP_DMA`** 等 | 约束 **物理地址范围**、用户可映射等 | 设备 DMA、用户页 |

**HFT 关联：** 热路径若在 **不当上下文** 触发 **`GFP_KERNEL` 回收** → **毫秒级 stall**；用户态 **mlock** 是为减少 **fault 路径进 allocator + reclaim**。

### 进程标志（突破水位）

内存紧张、低于 **pages_min** 时，普通分配可能被 **同步回收** 拖慢；带特殊标志的进程可 **绕过常规水位限制**：

| 标志 | 谁 |
|------|-----|
| **`PF_MEMALLOC`** | **`kswapd`** 等回收路径 — 需 **继续拿页完成回收** |
| **`PF_MEMDIE`** | 正被 **OOM killer** 处理的进程 |

→ [Ch 13 OOM](./chapter-13-内存耗尽管理.md) · Ch 1 路线 **`oom_kill.c`**

---

## 5. 避免碎片化 (Avoiding Fragmentation)

| 类型 | 含义 | Buddy 表现 |
|------|------|------------|
| **外部碎片** | 总空闲够，但 **没有足够大的连续物理块** | Buddy **拆分/合并** 专门缓解 |
| **内部碎片** | 只需 **1 小块**，却分到 **整页或多页**，页内浪费 | Buddy **按 2^n 页分配** → **易产生** |

**内部碎片 → Slab：** 内核大量 **小于一页** 的对象（`task_struct`、`inode`…）不直接用 Buddy 裸分，而由 **[Ch 8 Slab](./chapter-08-Slab分配器.md)** 在 **整页内切小对象**。

**HFT 用户态镜像：** **DPDK mempool**、**订单簿 arena** — 向 OS 要 **大页/大块**，内部 **自己切对象**，同一逻辑。

**大页 (huge order)：** 请求 **高 order** 或 **hugetlbfs** 需要 **长时间保持连续物理内存** — 外部碎片严重时会 **alloc 失败**（`ENOMEM`），即使 **总 free 内存不少**。

---

## 6. 2.6 内核的新变化

### 每 CPU 页面集合 (Per-CPU Page Lists · pageset)

| 问题 | 2.6 方案 |
|------|----------|
| 多核 **order-0（单页）** 分配极频 **`zone->lock` 争用** | 每 CPU **`pageset`**：**热页 / 冷页** 缓存 |
| 每次 alloc/free 都抢 zone 锁 | **0 阶** 多数路径 **无锁** 从 **本 CPU pageset** 取/还 |

与 [Ch 2 §2.6 pageset](./chapter-02-描述物理内存.md#每-cpu-页面集合-per-cpu-page-lists--pageset) 同一机制 — **读源码时 zone 结构和 page_alloc 要一起看**。

### 统一 NUMA API

2.4 UMA/NUMA **不同底层函数** → 2.6 **`numa_node_id()`** 等 **统一隐式 node 选择** — 应用仍可用 **`set_mempolicy`** 覆盖。

---

## Buddy 分配 + pageset 简图

```
                    alloc_pages(gfp, order)
                              │
              ┌───────────────┴───────────────┐
              │ order == 0 ?                  │
              └───────────────┬───────────────┘
                    是        │        否
                    ▼         │         ▼
            CPU pageset       │    zone->free_area[order]
            (hot/cold)        │         │
                    │         │    无块则 split 高 order
                    └─────────┴─────────┘
                              │
                    水位 / GFP / reclaim ?
                              │
                         struct page *
```

---

## HFT 精读 checklist

| 现象 | 查什么 |
|------|--------|
| **远程 NUMA 延迟** | 是否 **node-local** 分配；`numastat` |
| **latency 尖刺** | **direct reclaim**、**compaction**、**GFP** 上下文 |
| **大页分配失败** | **外部碎片** — 长期运行后 **2MB 连续物理页** 难拿 |
| **与 slab/mempool** | Buddy 管 **页**；热路径对象应用 **池化**（Ch 8 / DPDK） |
| **监控** | `/proc/vmstat`（`pgalloc_*`、`allocstall`** 等） |

---

## 相关章节

- 上一章：[chapter-05-启动内存分配器.md](./chapter-05-启动内存分配器.md)
- 下一章：[chapter-07-非连续内存分配.md](./chapter-07-非连续内存分配.md)
- 下一精读：[chapter-08-Slab分配器.md](./chapter-08-Slab分配器.md)（内部碎片）
- 附录 F：[appendix-F-物理页分配.md](./appendix-F-物理页分配.md)

---
