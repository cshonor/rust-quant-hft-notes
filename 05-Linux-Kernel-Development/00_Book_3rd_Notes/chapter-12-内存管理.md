# Ch 12 · 内存管理 · Memory Management

> **Linux Kernel Development 3rd** · Robert Love · **选读**  
> 本章定位：内核侧 **页、区、kmalloc/vmalloc、Slab、高端内存、per-CPU** — 与用户态 malloc/mmap **不同规则**。为 **Ch 15 进程地址空间**、**06 Gorman**、HFT **大页/mlock/零缺页** 补内核视角。

---

## 本节结构

| 节 | 主题 | 带走什么 |
|----|------|----------|
| **① 页** | `struct page` | 物理页 · `_count` |
| **② 区** | Zones | DMA · NORMAL · HIGHMEM |
| **③ 获得页** | `alloc_pages` | 连续物理页 |
| **④ kmalloc** | gfp_mask | **GFP_KERNEL vs ATOMIC** |
| **⑤ vmalloc** | 虚连续 | 大分配 · TLB 代价 |
| **⑥ Slab** | 对象缓存 | `task_struct` 等 |
| **⑦ 内核栈** | 静态分配 | **勿大数组** |
| **⑧ 高端内存** | kmap | 永久 vs 原子映射 |
| **⑨ per-CPU** | 每核副本 | 少锁 · 少 cache 颠簸 |

---

### 为何内核内存更复杂

| 用户空间 | 内核空间 |
|----------|----------|
| `malloc` 可触发复杂回收 | **不能轻易睡眠**（视上下文） |
| 页错误可换出 | **内核内存不可换页**（Ch 2） |
| 容错相对高 | 泄漏 = **直到重启** |

---

### ① 页 · Pages

**基本单元 = 物理页**（通常 **4KB**，架构相关）。

| 结构 | 说明 |
|------|------|
| **`struct page`** | 描述 **物理页本身** — **不是** 页内数据内容 |
| **`_count`** | **引用计数** |
| 计数 **< 0**（书中表述为降至负一语义） | 页 **空闲**，可分配 |

```
物理 RAM ──► 每页一个 struct page ──► 伙伴系统 / Slab 等分配器
```

→ **Ch 15** 用户页表映射这些物理页

---

### ② 区 · Zones

因 **DMA 寻址限制**、**32 位内核虚拟地址有限** 等，物理页划为 **区** 逻辑分组：

| 区 | 用途 |
|----|------|
| **ZONE_DMA** | 老式 DMA 可访问的低地址物理页 |
| **ZONE_DMA32** | 32 位 DMA 设备（较新） |
| **ZONE_NORMAL** | **永久映射** 进内核线性地址空间的页 |
| **ZONE_HIGHMEM** | **高端内存** — **不能** 永久内核映射（如 x86 32 位 **896MB 以上** 物理内存） |

```
低地址 ──► ZONE_DMA / DMA32 ──► ZONE_NORMAL ──► ZONE_HIGHMEM
              DMA 设备              内核直接映射        需 kmap 临时映射
```

> **64 位** 桌面/服务器常 **无 HIGHMEM** 痛点 — 概念仍用于理解 **DMA 区**。

---

### ③ 获得页 · Getting Pages

**页级**、**物理连续** 分配：

| API | 说明 |
|-----|------|
| **`alloc_pages()`** | 分配页（返回 `struct page *`） |
| **`__get_free_pages()`** | 返回 **逻辑地址** 指针 |
| **`get_zeroed_page()`** | 分配并 **清零** — 给用户空间前清敏感数据 |
| **`free_pages()`** 等 | **必须** 配对释放 — 否则 **内核泄漏** |

---

### ④ kmalloc() 与 kfree()

**按字节分配** — 类似用户态 `malloc`，但保证 **物理连续**。

```c
ptr = kmalloc(size, GFP_KERNEL);
kfree(ptr);
```

#### gfp_mask 常用标志

| 标志 | 行为 | 使用上下文 |
|------|------|------------|
| **`GFP_KERNEL`** | 常规；**可睡眠** 腾内存 | **进程上下文** — 成功率高 |
| **`GFP_ATOMIC`** | **绝不睡眠** | **中断、下半部、持 spinlock** — 紧张时 **易失败** |
| **`GFP_DMA`** | 从 **ZONE_DMA** 分配 | DMA 缓冲区 |

| 对比 Ch 5/10 | |
|--------------|--|
| syscall 里大块分配 | 常 `GFP_KERNEL` |
| ISR 里小缓冲 | **`GFP_ATOMIC`** + 短小 |

**HFT 用户态镜像：** 热路径 **预分配池** ≈ 避免 tick 内 `GFP_ATOMIC` 失败。

→ [01-CSAPP Ch9 malloc/池化](../../01-CSAPP-3rd/chapter-09-virtual-memory/)

---

### ⑤ vmalloc()

| 保证 | 说明 |
|------|------|
| **虚拟地址连续** | 改页表拼接零散物理页 |
| **物理 RAM 可不连续** | |

| 代价 | 原因 |
|------|------|
| **远大于 kmalloc** | **TLB 抖动**、更多页表遍历 |

| 典型用途 | 大块、非性能关键 — 如 **动态加载内核模块** 代码/数据 |

```
kmalloc：  物理连续 + 逻辑连续  → 快，适合中小对象
vmalloc：  仅虚连续            → 慢，适合大块
```

---

### ⑥ Slab 层 · Slab Layer

频繁分配/释放 **固定大小对象**（`task_struct`、inode…）→ **Slab 对象缓存**。

| 概念 | 说明 |
|------|------|
| **Cache** | 一种对象类型一条缓存 |
| **Slab** | 一条缓存里若干 **页块**，状态 **满 / 半满 / 空** |
| 分配策略 | 优先 **半满 Slab** 的空槽 — **快 + 减碎片** |

| API | 作用 |
|-----|------|
| **`kmem_cache_create()`** | 建自定义缓存 |
| **`kmem_cache_alloc()`** | 从缓存取对象 |
| **`kmem_cache_free()`** | 归还 |

→ **Ch 3** `task_struct` 由 Slab 分配

---

### ⑦ 在栈上的静态分配

| 事实 | 约束 |
|------|------|
| 内核栈 **小且固定** | 传统 **2 页（8KB）**；新内核可 **单页 4KB** |
| **禁止** 栈上大结构体/大数组 | **栈溢出** → 难查的破坏 |

| 规则 | 建议 |
|------|------|
| 局部变量合计 | **控制在几百字节内** |
| 大数据 | **`kmalloc` / Slab** |

→ **Ch 2** · **Ch 7** 中断栈

---

### ⑧ 高端内存的映射 · High Memory

`__GFP_HIGHMEM` 得到的页 **无永久内核线性地址** — 访问前须 **映射**：

| 方式 | API | 上下文 |
|------|-----|--------|
| **永久映射** | **`kmap()`** | **可睡眠** — **仅进程上下文** |
| **临时/原子映射** | **`kmap_atomic()`** | **不阻塞** · 临时 **关抢占** |
| 解除 | **`kunmap()` / `kunmap_atomic()`** | 必须配对 |

```
HIGHMEM 物理页 ──kmap_atomic──► 临时内核 VA ──访问──► kunmap_atomic
```

---

### ⑨ 每个 CPU 的分配 · Per-CPU

**SMP 优化** — 每处理器 **独立变量副本**：

| 收益 | 说明 |
|------|------|
| **少锁** | 本 CPU 通常只写自己的副本 |
| **少 cache thrashing** | 避免多核抢同一缓存行 |

| 接口（2.6+） | `percpu` 宏族 — 声明、分配、`__get_cpu_var` 等 |

→ **Ch 8** softirq per-CPU · **Ch 10** `preempt_disable` + per-CPU 数据

**HFT：** 用户态 **每线程/每核一条队列**（false sharing 意识）与内核 per-CPU 同构。

---

### 分配选型速查

| 需求 | API |
|------|-----|
| 若干连续物理页 | `alloc_pages` / `__get_free_pages` |
| 小对象、物理连续、快 | **`kmalloc`** |
| 中断/持锁、不能睡 | **`kmalloc(..., GFP_ATOMIC)`** |
| 大块、虚连续即可 | **`vmalloc`** |
| 固定类型高频对象 | **Slab / `kmem_cache_*`** |
| 每核私有计数/队列 | **per-CPU** |
| HIGHMEM 页访问 | **`kmap` / `kmap_atomic`** |

---

### Ch 12 小结

| 问题 | 答案 |
|------|------|
| 基本单元？ | **物理页** · `struct page` |
| 为何要 Zones？ | **DMA 限制** · **内核映射限制** |
| kmalloc vs vmalloc？ | **物理连续快** vs **虚连续大块慢** |
| GFP_KERNEL vs ATOMIC？ | **可睡** vs **原子上下文** |
| Slab 解决什么？ | **对象缓存** · 快 · 抗碎片 |
| 内核栈？ | **极小** — 大对象 **堆/Slab** |
| per-CPU？ | **少锁** · ** locality** |

---

### 检查单

- [ ] 解释 **`struct page` 描述物理页而非数据**
- [ ] 说出 **ZONE_NORMAL vs ZONE_HIGHMEM**（32 位语境）
- [ ] 区分 **`GFP_KERNEL` 与 `GFP_ATOMIC`** 使用场景
- [ ] 知 **vmalloc 的 TLB 代价**
- [ ] 联系 **Ch 3 Slab 分配 task_struct**
- [ ] HFT：对照用户态 **大页、mlock、对象池、NUMA 本地分配**

---

## 相关章节

- 上一章：[chapter-11-定时器和时间管理.md](./chapter-11-定时器和时间管理.md)
- 下一章：[chapter-13-虚拟文件系统.md](./chapter-13-虚拟文件系统.md)
- 深入：[06-Linux-Virtual-Memory-Manager](../../06-Linux-Virtual-Memory-Manager/) · [01-CSAPP Ch9](../../01-CSAPP-3rd/chapter-09-virtual-memory/)
- 本模块导读：[README.md](./README.md) · [OUTLINE.md](./OUTLINE.md)
