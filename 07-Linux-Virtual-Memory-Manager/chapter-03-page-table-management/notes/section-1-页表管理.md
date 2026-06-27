# Ch 3 页表管理 · Page Table Management

> **Understanding the Linux Virtual Memory Manager** · Mel Gorman · **精读**

本章讲 Linux 如何以 **与硬件体系结构无关** 的方式 **管理、组织页表** — 把线性（虚拟）地址 **逐级查表** 落到 **物理页框**（Ch 2 的 `struct page`）。

> **时代说明：** 原书以 **2.4 / 2.6**、**三级页表 (PGD → PMD → PTE)** 叙述（32 位 x86 / PAE 语境）。**x86_64 现代内核** 通常为 **四级**（PGD → PUD → PMD → PTE，见 `asm/pgtable*.h`）；**架构无关层** 仍用 `pgd_t` / `pmd_t` / `pte_t` 抽象，层数由 `CONFIG_PGTABLE_LEVELS` 决定。读源码以当前树为准。

> **HFT 延伸：** 透明大页 THP → [./note-透明大页THP.md](./note-透明大页THP.md)

---

## 本章在 VM 子系统中的位置

```
Ch 2：物理页框 (struct page) 在哪、属哪个 Zone
        ↓
Ch 3：页表 — 虚拟地址 → PTE → 物理 PFN
        ↓
Ch 4：每个进程的 mm_struct / VMA 如何挂在这套页表上
        ↓
Ch 10 / swap：改 PTE、rmap 解映射、换出
```

**HFT 为什么要读：** 每次 **TLB miss** 可能触发 **页表 walk**（多级指针 chasing，cache miss 链）；**大页** 减少 TLB 覆盖范围；**mlock** 保证 **PTE present**；**绑核 + 进程迁移** 涉及 **TLB flush**（`flush_tlb_*`）。

→ 交叉：[01-CSAPP Ch9 §9.6–9.7](../01-CSAPP-3rd/chapter-09-virtual-memory/) · [05-LKD Ch15 §15.7 页表](../05-Linux-Kernel-Development/00_Book_3rd_Notes/chapter-15-process-address-space/notes/section-15.7-页表.md)

---

## 1. 页目录与页表项 (PGD / PMD / PTE)

### 三级结构（原书 · 架构无关模型）

| 层级 | 名称 | 作用 |
|------|------|------|
| **PGD** | Page Global Directory · 页全局目录 | 每进程 **`mm_struct`** 有指向 **自身 PGD** 的指针 |
| **PMD** | Page Middle Directory · 页中间目录 | PGD 项指向 PMD 表 |
| **PTE** | Page Table Entry · 页表项 | PMD 项指向 PTE 表；**PTE 指向物理页框**（用户数据所在） |

```
线性地址  ──►  PGD[index0]  ──►  PMD[index1]  ──►  PTE[index2]  ──►  物理页框
                mm_struct->pgd
```

**x86_64 注：** 在 PGD 与 PMD 之间多一层 **PUD**（Page Upper Directory）；**Linux 通用宏**（`pgd_offset`、`p4d_offset`、`pud_offset`、`pmd_offset`、`pte_offset`）在各级 arch 上展开不同深度。

### 类型与地址拆分宏

| 类型 | 用途 |
|------|------|
| **`pgd_t` / `pmd_t` / `pte_t`** | 类型安全的页表项容器；支持 **PAE** 等扩展物理地址位宽 |
| **`SHIFT` / `SIZE` / `MASK` 宏** | 把 **线性地址** 拆成各级 **索引偏移** |

### PTE 保护位与状态位（示例）

| 位 / 宏 | 含义 |
|---------|------|
| **`PAGE_PRESENT`** | 页在 **内存中**（非 swap / 非 hole） |
| **`PAGE_RW`** | **可写** |
| **`PAGE_USER`** | **用户态** 可访问（无则仅内核） |
| **`PAGE_DIRTY`** | 已被写入 — **脏页**，需写回 |
| **`PAGE_ACCESSED`** | 被访问过 — LRU / 回收参考（常对应 **young** 位） |

→ 与 Ch 2 **`PG_dirty` / `PG_active`** 等 **struct page flags** 协同；换出、写回路径会 **同时** 动 PTE 与 page flags。

---

## 2. 遍历与使用页表 (Using Page Table Entries)

内核频繁 **页表遍历 (page table walk)** — 缺页、munmap、mprotect、swap、debugger 等。

### 定位各级表项

| 宏（原书） | 作用 |
|------------|------|
| **`pgd_offset()`** | 由线性地址 + `mm` 得 **PGD 项** |
| **`pmd_offset()`** | 得 **PMD 项** |
| **`pte_offset()`** | 得 **PTE 项** |

（现代树在深层 arch 上可能先经 **`p4d_offset` / `pud_offset`**。）

### 检查 / 修改 PTE 状态

| 宏 | 作用 |
|----|------|
| **`pte_present()`** | 是否在内存 |
| **`pte_dirty()` / `pte_mkdirty()`** | 读/设 dirty |
| **`pte_young()` / `pte_mkyoung()`** | 读/设 accessed（young） |
| **`set_pte()` / `pte_clear()`** | 安装 / 清除映射 |

**HFT：** 热路径 **用户态** 不跑这些宏；但 **prefault、mlock、大页合并/分裂** 会在内核里 **批量改 PTE** → 触发 **TLB shootdown**。

---

## 3. 页表的分配与释放 (Quicklists)

分配 **物理页** 作页表本身（PGD/PMD/PTE 表占用的页）**昂贵** — 常需 **关中断 / 拿锁**。

**2.4/2.6 快速缓存 (Quicklists)：**  per-CPU 或全局 **LIFO 链表** 缓存刚释放的页表页：

| Quicklist | 缓存对象 |
|-----------|----------|
| **`pgd_quicklist`** | PGD 级表页 |
| **`pmd_quicklist`** | PMD 级表页 |
| **`pte_quicklist`** | PTE 级表页 |

**LIFO** → 刚释放的页更可能 **仍在 cache 热**，加速 **fork / munmap / 缺页** 路径。

> **现代内核：** quicklist 概念演化为 **专用 slab / kmem_cache**（如 `pgtable_cache`）；**思想不变** — **不要每次 walk 到 buddy 分配器**。

---

## 4. 内核页表初始化 (Kernel Page Tables)

分页 **非上电即有** — 启动时分阶段建立。

| 阶段 | 做什么 |
|------|--------|
| **引导 (Bootstrapping)** | 仅为 **前 8MiB** 物理内存建页表 — 够 **开启 MMU / 分页单元** |
| **最终化 (Finalizing)** | **`paging_init()`** → **`pagetable_init()`** 等 — 为 **`ZONE_DMA` + `ZONE_NORMAL`** 建立 **内核线性映射**，并初始化 zone 等 |

**用户进程页表** 在 **fork / exec / mmap** 时逐步填充；**内核部分** 在 boot 末段 **全局就绪**。

→ 与 [Ch 5 启动内存分配器](../../chapter-05-boot-memory-allocator/notes/section-1-启动内存分配器.md) 衔接（boot 页分配器 vs 正式 page allocator）。

---

## 5. 地址与 struct page 的映射

内核需在 **物理地址 ↔ 虚拟地址 ↔ struct page** 之间 **快速转换**。

### 物理地址 ↔ 内核虚拟地址（ZONE_NORMAL）

在 **内核直接映射区**（x86 32 位上约 **3GiB 起 `PAGE_OFFSET`**）：

| 方向 | 思路 |
|------|------|
| 物理 → 虚拟 | **`phys + PAGE_OFFSET`**（宏 **`__va()`** / **`phys_to_virt()`**） |
| 虚拟 → 物理 | 减 **`PAGE_OFFSET`**（**`__pa()`** / **`virt_to_phys()`**） |

**仅适用于「线性映射窗口」内的物理页** — HIGHMEM 需 `kmap`（Ch 2 §4）。

### 物理地址 → struct page

1. 物理地址 **右移** 得到 **页框号 PFN**
2. 全局 **`mem_map[]`**（现代：**sparse vmemmap** / **pfn_to_page**）— **PFN 作索引** 取 **`struct page`**
3. 宏 **`virt_to_page()`** / **`pfn_to_page()`** 封装上述逻辑

```
PFN  ──index──►  mem_map[PFN]  ==  struct page  （Ch 2）
                      ▲
PTE ──frame number──┘
```

→ **页表管「虚拟→物理」；mem_map/ vmalloc 管「物理→struct page 元数据」**。

---

## 6. TLB 与 L1 Cache 管理

CPU 用 **TLB** 缓存 **最近用过的 VA→PA**；**L1 cache** 缓存 **物理帧内容**。页表更新后，硬件 **不一定** 自动使旧 TLB/cache 项失效。

Linux 在 **改映射、切换 mm、换页** 等路径插入 **架构相关 hook**：

| Hook（示例） | 何时需要 |
|--------------|----------|
| **`flush_tlb_all()`** | 全局 TLB 失效 |
| **`flush_tlb_mm()`** | 某 **`mm_struct`** 的 TLB 项 |
| **`flush_tlb_page()`** | 单页 |
| **`flush_cache_mm()` / `flush_cache_page()`** | 某些 arch 上 **cache alias** / **coherency** |

**上下文切换** 换 **`mm`** → 常 **切换页表基址 + 部分 flush** — **多线程绑核** 可减少 **跨核 TLB shootdown**（仍与 **页表共享** 策略有关）。

**HFT：**

| 现象 | 页表/TLB 视角 |
|------|----------------|
| **工作集 > TLB 覆盖** | **TLB miss** ↑ → 页表 walk ↑ → 延迟尾 |
| **4KiB 小页** | 同样 1GiB 映射需 **更多 PTE / 更多 TLB 项** |
| **2MiB / 1GiB 大页、THP** | **更少 PTE、更少 TLB miss** — HFT 常 **显式 hugepage** 或 **关 THP 防 latency 抖动**（见 THP 笔记） |
| **进程迁移到其他 CPU** | 可能 **remote TLB invalidation** |

→ [Hennessy Ch2 TLB](../02-Computer-Architecture-6th/chapter-02-memory-hierarchy-design/) · [10-DPDK EAL 大页](../14-DPDK-Low-Latency-Network/01-Intro-Book/notes/chapter-01-DPDK架构与EAL/)

---

## 7. 2.6 内核的新变化 (What's New in 2.6)

### 无 MMU 架构 (`mm/nommu.c`)

为 **无 MMU** 微控制器提供 **nommu** 路径 — 无硬件页表，**uClinux** 等场景；与 **HFT 服务器** 关系不大，知道 **Linux MM 有 fork** 即可。

### 反向映射 (Reverse Mapping · rmap) — **重点**

| 2.4 痛点 | 2.6 rmap |
|----------|----------|
| **共享页** 换出时需 **扫描所有进程页表** 找指向该页的 PTE — **O(进程×页表)** | 每个 **`struct page`** 挂 **映射它的 PTE 链表 (anon_vma / address_space)** |
| 解除映射慢、难原子 | **直接找到并解除所有 PTE**，换出 (**pageout**) **快得多** |

**至今仍是核心：** 现代 **`mm/rmap.c`** — **RMAP** 与 **LRU 回收、swap、munmap、madvise** 交织。

```
共享物理页 P
    struct page ──► rmap 链表 ──► [mm₁,vma₁,pte₁] [mm₂,vma₂,pte₂] …
    换出时：沿链表 clear PTE，而非扫全局
```

→ [Ch 10 页框回收](../../chapter-10-page-frame-reclamation/notes/section-1-页框回收.md) · [Ch 12 共享内存](../../chapter-12-shared-memory-virtual-filesystem/notes/section-1-共享内存虚拟文件系统.md)（文件页 rmap 经 **address_space**）。

### 高端内存中的 PTE (PTEs in High Memory)

大内存机器上 **PTE 表本身** 也可能占满 **ZONE_NORMAL** 低端：

- 2.6 允许 **PTE 页分配在 ZONE_HIGHMEM**
- 访问时用 **`pte_offset_map()`** **临时映射** 到低端可触达虚拟地址，用完 **`pte_offset_unmap()`**

**64 位** 上问题缓解，但 **「页表本身也占物理内存、也占低端窗口」** 的思想仍在 **内存紧张 / 嵌入式** 场景出现。

---

## 三级页表 + 地址转换一图（原书模型）

```
                    mm_struct
                        │
                        ▼
              ┌─────────────────┐
    VA ──────►│ PGD ──► PMD ──► PTE ──► PFN ──► struct page
              └─────────────────┘
                        │
              PTE bits: PRESENT RW USER DIRTY ACCESSED …
                        │
              TLB 缓存 VA→PA；未命中则 walk 上述层级
```

---

## HFT 精读 checklist

| 主题 | 行动 |
|------|------|
| **TLB / 页表 walk** | 压工作集、**大页**、减少 pointer chasing 数据结构 |
| **PTE present + mlock** | 避免 **缺页** 与 **swap** 路径 |
| **flush_tlb_*** | 理解 **绑核**、**减少跨核页表改动** |
| **rmap** | 理解 **共享内存 / mmap 文件** 换出成本 — 多映射页更「重」 |
| **THP** | 在 **减少 TLB miss** 与 **合并延迟抖动** 之间取舍 → [./note-透明大页THP.md](./note-透明大页THP.md) |

---

## 相关章节

- 上一章：[../../chapter-02-describing-physical-memory/notes/section-1-描述物理内存.md](../../chapter-02-describing-physical-memory/notes/section-1-描述物理内存.md)
- 下一章：[../../chapter-04-process-address-space/notes/section-1-进程地址空间.md](../../chapter-04-process-address-space/notes/section-1-进程地址空间.md)
- 附录 C：[appendix-C-页表管理.md](../../appendix-C-页表管理.md)

---
