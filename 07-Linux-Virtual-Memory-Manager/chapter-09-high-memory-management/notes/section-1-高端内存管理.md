# Ch 9 高端内存管理 · High Memory Management

> **Understanding the Linux Virtual Memory Manager** · Mel Gorman · **跳过**（**x86_64 HFT 机器通常无 `ZONE_HIGHMEM`** — 读作 **32 位 / PAE 历史** + **DMA 寻址限制** 背景；**`mempool` 概念** 见 [Ch 8](../../chapter-08-slab-allocator/notes/section-1-Slab分配器.md)）

## 问题从哪来

**32 位 x86** 典型划分：**3GiB 用户 + 1GiB 内核**（`PAGE_OFFSET = 0xC0000000`）。

| 区域 | 大致范围 | 内核能否 **直接** 用虚拟地址访问 |
|------|----------|----------------------------------|
| **`ZONE_NORMAL`** | 低端物理 RAM（原书约 **896MiB** 直接映射窗口） | **能** — `__va(pfn)` 线性映射 |
| **`ZONE_HIGHMEM`** | 超出直接映射窗口的物理 RAM | **不能** — 必须 **临时映射** |

物理内存 **> ~1GiB**（PAE 下可达 **64GiB**）时，大量页框落在 **HIGHMEM** — 内核 **不能** 像 touch `ZONE_NORMAL` 那样 **直接 dereference** 对应物理页。

→ 铺垫：[Ch 2 §4 高端内存](../../chapter-02-describing-physical-memory/notes/section-1-描述物理内存.md#4-高端内存-high-memory) · [Ch 3 §5 物理↔虚拟](../../chapter-03-page-table-management/notes/section-1-页表管理.md#5-地址与-struct-page-的映射)

**x86_64：** 内核 **64 位 canonical 地址 + 巨大直接映射**，**HIGHMEM 通常为空** — 本章机制 **多数不跑**；但 **bounce buffer / 设备 DMA 掩码** 在 **「设备只能看低 4G 物理地址」** 时仍相关。

---

## 本章在 VM 子系统中的位置

```
Ch 2 ZONE_HIGHMEM 页框存在，但内核不能常触
        ↓
Ch 9 kmap / bounce / emergency pool  ← 本章
        ↓
Ch 10 回收、I/O 路径可能 touch HIGHMEM 页
Ch 8 mempool — 2.6 从 emergency pool 泛化而来
```

**HFT（64 位）：** 不必背 PKMap 细节；理解 **「不能假设所有 RAM 都能零成本 kernel 直接访问」** 与 **DMA 缓冲在「设备可见物理区」** 即可 — 对照 **DPDK 在 DMA 区分配 mbuf**。

---

## 1. PKMap 地址空间管理

内核在 **页表顶部** 保留 **持久内核映射 (Persistent Kernel Mapping, PKMap)** 窗口：

```
    高地址
    FIXADDR_START   ─── 固定映射区（如 APIC）
    …
    PKMAP_BASE      ═══ PKMap 区（约 <32MiB，~1024 页槽位）
    …
    PAGE_OFFSET     ─── 常规内核线性映射
```

| 概念 | 说明 |
|------|------|
| **`PKMAP_BASE` ~ `FIXADDR_START`** | **临时** 把 **HIGHMEM 物理页** 映射进 **内核可访问 VA** |
| **池很小** | 同时 **~1024** 个高端页映射 — **必须短借短还** |

**设计约束：** PKMap 是 **稀缺槽位** — 占着不 **`kunmap`** 会 **饿死** 其他需要 kmap 的路径。

---

## 2. 映射与解除映射高端页

### 常规：`kmap()` / `kunmap()`

```
struct page *page  (HIGHMEM)
    kmap(page)  → 内核可用的 void *vaddr（占用 PKMap 槽）
    … 内核读写该页 …
    kunmap(page) → 释放 PKMap 槽
```

| 特点 | 说明 |
|------|------|
| **可能睡眠** | PKMap 满时需 **等待** 槽位 — **不可在中断里用** |
| **必须配对 kunmap** | 否则 **映射泄漏** |

### 原子：`kmap_atomic()` / `kunmap_atomic()`

| 特点 | 说明 |
|------|------|
| **不睡眠** | 供 **中断 / 原子上下文** |
| **每 CPU 预留槽** | 每核 **固定用途** 的页表项 — **极快** |
| **必须同 CPU 配对 unmap** | 槽位 **CPU 私有** |

→ 与 [Ch 6 `GFP_ATOMIC`](../../chapter-06-physical-page-allocation/notes/section-1-物理页分配.md#4-gfp-标志与进程标志-gfp--process-flags) 同类：**硬上下文不能用会睡的路径**。

**现代 x86_64：** 大量原 **HIGHMEM kmap** 路径 **不再执行**；**`kmap_local_page`** 等是后续演进 — 思想仍是 **临时内核 VA 窗口**。

---

## 3. 回弹缓冲区 (Bounce Buffers)

**场景：** 设备 **DMA 只能寻址低端物理地址**（32 位设备接 64 位机、PAE、部分旧控制器）— **无法** 直接读写 **HIGHMEM 物理页**。

```
设备 DMA 写 ──► 低端 bounce buffer（ZONE_DMA / 设备可见区）
                    │
                    ▼ 内核 memcpy
              HIGHMEM 目标 struct page
```

| 方向 | 流程 |
|------|------|
| **设备 → 内存（读盘/网卡入）** | 数据先进 **bounce** → **复制** 到高端目标页 |
| **内存 → 设备（写）** | 从高端页 **复制到 bounce** → 设备 DMA |

**代价：** **多一次完整拷贝** — 仍可能比 **为腾 LOWMEM 而 swap 整进程** 便宜。

**HFT 现代对照：** **NIC DMA 到 registered 物理地址** — 必须 **在设备 `dma_mask` 内** 分配缓冲（**ibverbs / DPDK memzone**）；不是 HIGHMEM，但是 **同一「硬件看不见高物理地址」** 问题。

---

## 4. 紧急内存池 (Emergency Pools)

**死锁场景：** HIGHMEM I/O 需要 **LOWMEM 做 bounce** → LOWMEM 耗尽 → **I/O 挂起** → 进程阻塞 **无法释放内存** → **无法前进**。

内核为 **bounce** 等保留 **紧急池**：

| 池 | 保留对象 |
|----|----------|
| **页面池** | 至少若干 **可立即用于 bounce 的页** |
| **`buffer_head` 池** | 块 I/O 路径关键结构 |

**保证：** 内存 **再紧** 也能 **完成少量关键 HIGHMEM I/O** — 避免 **全局僵局**。

→ 2.6 泛化为 **[Ch 8 `mempool`](../../chapter-08-slab-allocator/notes/section-1-Slab分配器.md#内存池-mempool)** — **任何子系统** 可 **预 reserve 关键对象**。

---

## 5. 2.6 内核的新变化

| 变化 | 说明 |
|------|------|
| **通用 `mempool`** | 2.4 **HIGHMEM 专用** emergency pool → 2.6 **`mempool_t`** 全内核可用 |
| **移除 `page->virtual`** | 2.4 在 **`struct page`** 存 PKMap 的 **vaddr** — 海量 page 结构 **浪费内存**；2.6 **删除**，改用 **其他映射跟踪** |

**HFT：** **`struct page` 体积** 影响 **mem_map / vmemmap 内存开销** — 现代仍强调 **page 结构紧凑**（**compound page、THP** 等叠在上）。

---

## HIGHMEM 访问路径一图（32 位）

```
HIGHMEM struct page
        │
        ├─ 内核要读写内容
        │      kmap / kmap_atomic → PKMap VA → 访问
        │      kunmap / kunmap_atomic
        │
        └─ 设备 DMA
               bounce buffer (LOWMEM) ↔ memcpy ↔ HIGHMEM page
               emergency pool 保底 bounce 分配
```

---

## HFT / 阅读建议

| 读者 | 建议 |
|------|------|
| **x86_64 HFT** | **跳过正文**；记住 **Ch 2 HIGHMEM 为何存在**、**DMA 物理地址可见性** |
| **嵌入式 / 32 位** | 精读 **kmap / bounce** |
| **与 Ch 8 衔接** | **emergency pool → mempool** — 关键路径 **reserve** 思想 |
| **继续** | [Ch 10 页框回收](../../chapter-10-page-frame-reclamation/notes/section-1-页框回收.md) |

---

## 相关章节

- 上一章：[../../chapter-08-slab-allocator/notes/section-1-Slab分配器.md](../../chapter-08-slab-allocator/notes/section-1-Slab分配器.md)
- 下一章：[../../chapter-10-page-frame-reclamation/notes/section-1-页框回收.md](../../chapter-10-page-frame-reclamation/notes/section-1-页框回收.md)
- 附录 I：[appendix-I-高端内存管理.md](../../appendix-I-高端内存管理.md)
- Ch 3 PTE in HIGHMEM：[../../chapter-03-page-table-management/notes/section-1-页表管理.md](../../chapter-03-page-table-management/notes/section-1-页表管理.md#高端内存中的-pte-ptes-in-high-memory)

---
