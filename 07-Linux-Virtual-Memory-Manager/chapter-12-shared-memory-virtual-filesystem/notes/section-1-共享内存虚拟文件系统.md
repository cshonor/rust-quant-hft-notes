# Ch 12 共享内存虚拟文件系统 · Shared Memory Virtual Filesystem

> **Understanding the Linux Virtual Memory Manager** · Mel Gorman · **选读**（HFT：**跨进程共享行情 / ring buffer** 常走 **`mmap(MAP_SHARED)`** — 文件映射或 **`/dev/shm` tmpfs**；本章解释 **匿名共享** 如何 **伪装成文件页** 走统一 VM 路径）

## 问题：匿名共享没有「真文件」

| 场景 | 后备存储 |
|------|----------|
| **`mmap` 真实文件 + `MAP_SHARED`** | 磁盘文件 — 复用 **page cache + address_space**（Ch 10） |
| **匿名 `MAP_SHARED`**（无 fd） | **无物理文件** — 不能直接用现有 **文件页** 管理接口 |
| **System V `shmget()` / `shmat()`** | 同样 **无磁盘文件** |

内核解法：在 **RAM 里造一个虚拟文件系统** — 给匿名共享页 **伪装的 file backing**，让 **缺页、swap、LRU** 等 **按文件映射同一套逻辑** 处理。

→ [Ch 4 mmap](../../chapter-04-process-address-space/notes/section-1-进程地址空间.md#3-内存区域-memory-regions--vma) · [Ch 11 共享页 swap](../../chapter-11-swap-management/notes/section-1-交换管理.md#4-交换缓存-swap-cache--核心)

> **源码：** 现代主线 [`mm/shmem.c`](https://elixir.bootlin.com/linux/latest/source/mm/shmem.c)（tmpfs/shmem 合一）· 挂载点 **`/dev/shm`**、**`/tmp`**（tmpfs）。

---

## 1. shm 与 tmpfs

| 变体 | 谁可见 | 用途 |
|------|--------|------|
| **`shm`** | **内核内部挂载**，用户 **不可见** | **匿名 MAP_SHARED**、**SysV shm** 的 **内部后备** |
| **`tmpfs`** | 管理员挂载 — **`/tmp/`、`/dev/shm/`** 等 | **RAM 临时文件系统** — 用户 **mmap tmpfs 文件** 做 IPC |

**共同点：** 数据 **只在内存**（+ swap 可能），**极快** — HFT 常用 **`/dev/shm/my_ring`** 或 **memfd_create**（现代，后于原书）映射共享区。

```
用户：mmap(/dev/shm/feed, MAP_SHARED)
内核：走 tmpfs → shmem 页 → 多进程共享同一 struct page（rmap）
```

---

## 2. 初始化与文件操作

### `init_tmpfs()` 与 `shmem_inode_info`

| 组件 | 作用 |
|------|------|
| **`init_tmpfs()`** | 注册并挂载 **shm / tmpfs** |
| **`shmem_inode_info`** | 每个 **inode 私有数据** — 管 **页树、swap 向量、已分配页计数** 等 |

### 文件 ops（原书）

**`mmap` · `read` · `write` · 目录/链接 · truncate** — 与 **普通 FS** 接口一致。

| 特例 | 原因 |
|------|------|
| **`fsync` 空操作** | 数据 **仅在 RAM** — **无需刷盘**（除非 swap） |

**HFT：** 共享 ring **write 后无 fsync 成本** — 但需 **用户态内存屏障 / 原子序** 做 **进程间同步**（不属于 VM 章，但别误以为 fsync 能代替）。

---

## 3. 缺页与 Swap（共享 shmem 页）

### 私有匿名页 vs 共享 shmem 页（换出时）

| | **私有匿名页** | **共享 shmem / tmpfs 页** |
|---|----------------|---------------------------|
| **swap 位置存哪** | **各进程 PTE** 里的 **`swp_entry`** | PTE **清零**；位置存 **inode 私有数据**（**类 ext2 块索引**） |
| **原因** | 单进程映射 | **多 PTE 映射同一页** — **统一由 inode 管 swap 索引** |

**inode 内 swap 管理（原书）：** 借用 **直接块 + 间接块** 思想 — 在 **`shmem_inode_info`** 里存 **页索引 → swp_entry** 向量。

### 缺页路径

**`shmem_nopage` / `shmem_getpage`**（现代 **`shmem_fault`** 等）：

```
fault on shmem VMA
    → 查 inode 页树 / swap 索引
    → 若在 swap：读盘（Ch 11）
    → 若未分配：alloc 新页（零页或 demand）
    → 安装 PTE present
```

→ [Ch 3 rmap](../../chapter-03-page-table-management/notes/section-1-页表管理.md#反向映射-reverse-mapping--rmap--重点) — **多进程共享** 时 **换出/换入** 仍依赖 **rmap + swap cache**（Ch 10–11）。

---

## 4. 建立共享区与 System V IPC

### 匿名 `MAP_SHARED` → `shmem_zero_setup()`

```
mmap(MAP_SHARED | MAP_ANONYMOUS, …)
    → shmem_zero_setup()
    → 在内部 shm _fs 静默创建 **dev/zero** 类虚拟文件
    → do_mmap 映射该 inode
```

**效果：** 用户以为是 **匿名共享内存**；内核看来是 **shmem 文件映射** — **统一 VM 路径**。

### System V：`shmget()` / `shmat()` 揭秘

| 用户 API | 内核实际 |
|----------|----------|
| **`shmget(key, size, …)`** | 在 **shm fs** 创建内部文件 **`SYSVNN`**（NN = key 编码） |
| **`shmat()`** | **`do_mmap()`** 把该 **虚拟文件** 映射进进程地址空间 |

**现代对照：** **POSIX shared memory**（`shm_open`）常映射 **`/dev/shm/xxx`** — 同样 **tmpfs/shmem** 后端。

**HFT：** 多进程 **读同一块 mmap 行情** = **MAP_SHARED shmem 页** + **用户态 seqlock/atomic**；**写时 COW 不共享** — 须 **SHARED** 而非 **PRIVATE**（Ch 4 COW）。

---

## 5. 2.6 内核的新变化

| 改进 | 说明 |
|------|------|
| **`shmem_inode_info.alloced`** | 记录 **已分配页数** — 免 2.4 **动态遍历计数** |
| **`VM_ACCOUNT`** | **精确内存配额** — 防 **overcommit** 下 shmem **无限涨** |
| **`llseek` / `sendfile`** | 扩展文件语义 |
| **非线性映射 (nonlinear mappings)** | 大文件 **稀疏 / 特定页映射** 优化 |
| **专用 inode slab cache** | inode **快速分配/回收** |

**HFT 延伸：** **`memfd_create` + sealing**（现代 Linux）— **仍走 shmem** — 创建 **无路径的 RAM 文件** 再 **mmap**，比 **SysV key** 更易用。

---

## 两条 IPC 路径一图

```
                    进程 A          进程 B
                       │               │
    真实文件 MAP_SHARED ├───────────────┤  page cache 同一 struct page
                       │               │
    tmpfs 文件 mmap     ├───────────────┤  shmem inode 页树
    (/dev/shm/x)       │               │
                       │               │
    MAP_SHARED 匿名     ├───────────────┤  内部 dev/zero shmem 文件
                       │               │
    SysV shmget/shmat   ├───────────────┤  内部 SYSVNN shmem 文件
```

---

## HFT 精读 checklist

| 需求 | 做法 |
|------|------|
| **跨进程零拷贝读行情** | **`mmap MAP_SHARED`** on **tmpfs 文件** 或 **memfd** |
| **避免 swap 拖慢共享区** | **`mlock` 映射区** · 足够 RAM |
| **理解 swap 行为** | 共享 shmem 页 swap 索引在 **inode** — **换入一次** 多 PTE 受益 |
| **别用 MAP_PRIVATE 当共享** | PRIVATE → **COW** — 各进程 **各一份** |
| **与 Ch 10 LRU** | shmem 页在 **page cache / LRU** — 内存紧时 **可被回收**（除非 mlock） |

---

## 相关章节

- 上一章：[../../chapter-11-swap-management/notes/section-1-交换管理.md](../../chapter-11-swap-management/notes/section-1-交换管理.md)
- 下一章：[../../chapter-13-out-of-memory-management/notes/section-1-内存耗尽管理.md](../../chapter-13-out-of-memory-management/notes/section-1-内存耗尽管理.md)
- 附录 L：[appendix-L-共享内存虚拟文件系统.md](../../appendix-L-共享内存虚拟文件系统.md)
- 用户态 IPC：[08-TLPI](../08-The-Linux-Programming-Interface/) · SysV / POSIX shm

---
