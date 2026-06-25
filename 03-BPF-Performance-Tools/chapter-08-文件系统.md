# Ch 8 文件系统 · File Systems

> **BPF Performance Tools** · Brendan Gregg · **跳过 ⚪**

> 本章定位：**应用程序视角的逻辑 I/O** — 应用通常不直接碰磁盘，而是经 **VFS + 页缓存** 读写。文件系统用 **缓存、预读、写回、异步 I/O** 把物理盘延迟藏起来；BPF 工具测量的是 **应用在逻辑 I/O 上真实等待的时间**。  
> **HFT：** 热路径应 **无同步盘 I/O**（行情/下单走内存、网络、DPDK）；本章默认 **⚪ 跳过**，仅在 **日志风暴、`mmap` 数据文件、配置热读、共置机 page cache 争抢** 等 incident 时查阅 `opensnoop` / `cachestat` / `fileslower`。  
> **上一章：** [chapter-07-内存.md](./chapter-07-内存.md) · **下一章：** [chapter-09-磁盘IO.md](./chapter-09-磁盘IO.md)

---

## 1. 本章要回答的问题

| 传统误区 | 本章视角 |
|----------|----------|
| 只看磁盘 I/O | 先看 **逻辑 I/O** 与 **缓存命中** |
| `iostat` 不忙但应用慢 | VFS 层 **`fileslower`**、**`ext4dist`** |
| 不知在读哪个文件 | **`filetop`**、**`opensnoop`** |
| 缓存是否有效 | **`cachestat`** 命中率 |

```
应用程序 read/write/mmap
        ↓
   VFS（opensnoop / vfsstat / fileslower）
        ↓
  页缓存 / dcache / inode cache（cachestat / readahead / writeback）
        ↓
  具体 FS：ext4 / xfs（ext4dist / xfsslower）
        ↓
  块设备 ——→ [Ch 9 磁盘 I/O](./chapter-09-磁盘IO.md)
```

---

## 2. 文件系统基础 (Background)

### 逻辑 I/O vs 物理 I/O

| 类型 | 说明 |
|------|------|
| **逻辑 I/O** | 应用 `read`/`write`/`mmap` 对 **文件** 的请求 |
| **物理 I/O** | 真正下到块设备的 I/O |

**页缓存命中** 时，逻辑读 **不** 产生物理读 — 延迟在内存量级。

### 三大缓存

| 缓存 | 作用 | 占用 |
|------|------|------|
| **Page Cache** | 文件内容与 I/O 缓冲 | 通常 **最大** |
| **Inode Cache** | inode 元数据、权限 | 中等 |
| **dcache** | 路径名 → inode 映射 | 加速路径查找 |

→ 内核实现：[05-LKD VFS](../05-Linux-Kernel-Development/00_Book_3rd_Notes/chapter-13-vfs/) · [08-ULK](../08-Understanding-Linux-Kernel/) · [01-30days-os Day 18–19 FAT](../09-system-low-level-hands-on/01-30days-os/day-18-dir/)

### 预读与写回

| 机制 | 行为 |
|------|------|
| **Read-ahead** | 检测顺序读 → **提前** 读入后续页到 cache |
| **Write-back** | 脏页驻留内存 → **异步** 刷盘，避免阻塞写路径 |

**调优陷阱：** 预读过激 → 浪费内存与 I/O（`readahead` 工具可见 **预读但未使用** 的页）。

---

## 3. 传统文件系统工具

| 工具 | 用途 | 注意 |
|------|------|------|
| `df -h` | 文件系统容量 | |
| `mount` | 挂载选项（`noatime`、`barrier`…） | |
| `strace -e open,read,write` | 系统调用级追踪 | **开销极高** — 仅短跑 |
| `perf trace` | 轻量 syscall 采样 | 比 strace 克制 |
| `fatrace` | fanotify 文件访问 | 专用、有场景 |

```bash
df -h
mount | grep -E 'ext4|xfs'
```

**BPF 价值：** 比 `strace` 更适合 **生产短窗口** — 内核聚合、可限频率。

---

## 4. VFS 与应用 I/O 分析

### `opensnoop`

追踪 **`open()` / `openat()`** — 系统范围。

```bash
sudo opensnoop-bpfcc
sudo opensnoop-bpfcc -p $(pidof myapp)
```

| 场景 | 价值 |
|------|------|
| 找不到配置文件 | 看失败路径 |
| 日志路径、意外文件访问 | 审计热路径是否碰盘 |

→ 亦见 [Ch 4 BCC 单用途工具](./chapter-04-BCC.md)

### `vfsstat` / `vfscount` / `vfssize`

| 工具 | 输出 |
|------|------|
| `vfsstat` | VFS 操作 **速率**（读/写/打开/创建…） |
| `vfscount` | 按操作类型 **计数** |
| `vfssize` | 读写 **大小分布直方图** |

```bash
sudo vfsstat-bpfcc 1
sudo vfssize-bpfcc 10
```

**用途：** 极高层的 **工作负载表征** — 读多还是写多、请求块大小。

### `fsrwstat`

类似 `vfsstat`，但按 **文件系统类型** 分类：`ext4`、`xfs`、`sockfs`、`sysfs`…

```bash
sudo fsrwstat-bpfcc 5
```

**场景：** 区分 **真实磁盘 FS** vs **伪文件系统** 流量。

### `filetop`

像 `top` 一样列出 **当前读写最频繁 / 吞吐量最高** 的文件。

```bash
sudo filetop-bpfcc
```

**HFT incident：** 谁在打满磁盘日志或意外写大文件。

### `fileslower`

打印慢于阈值的 **同步** 文件读写（默认如 **10ms**）。

```bash
sudo fileslower-bpfcc 10
sudo fileslower-bpfcc -p $(pidof myapp) 5
```

**直接定位** 拖慢应用的 **逻辑 I/O** — 在 blame 磁盘前先跑此工具。

---

## 5. 缓存效能分析

### `cachestat` — 页缓存命中率 🔴

显示 **页缓存 HIT / MISS** 及 **命中率 (HITRATIO)**。

```bash
sudo cachestat-bpfcc 1
```

| 解读 | 含义 |
|------|------|
| 命中率高 | 工作集在内存内 — 物理 I/O 少 |
| 命中率骤降 | 工作集 > RAM 或冷启动 — 衔接 [Ch 7](./chapter-07-内存.md) / [Ch 9](./chapter-09-磁盘IO.md) |
| DB / 时序库调优 | 数据集是否 **fit in cache** |

**经典组合：** `cachestat` 命中高 + `ext4dist` 写延迟大 → 问题可能在 **写回/fsync**，而非读缓存。

### `writeback`

追踪 **脏页写回** 磁盘：刷新页数、耗时、触发原因（周期、内存压力…）。

```bash
sudo writeback-bpfcc
```

**场景：** 延迟尖刺与 **后台 flush** 同相。

### `readahead`

追踪 **预读** 行为 — 含 **预读但从未访问** 的页比例。

```bash
sudo readahead-bpfcc
```

**调优：** 顺序大文件读可受益；随机小读可能 **浪费**。

### `dcstat` / `dcsnoop`

| 工具 | 作用 |
|------|------|
| `dcstat` | **dcache** 命中率统计 |
| `dcsnoop` | 目录查找详情（路径解析） |

```bash
sudo dcstat-bpfcc 1
```

### `icstat`

按秒统计 **inode cache** 引用、未命中、命中率。

```bash
sudo icstat-bpfcc 1
```

---

## 6. 内存映射与文件生命周期

### `mmapfiles` / `fmapfault`

**mmap** 也是 I/O 路径 — 不一定经过 `read()`。

| 工具 | 作用 |
|------|------|
| `mmapfiles` | 追踪通过 mmap 的文件访问 |
| `fmapfault` | 映射文件的 **缺页** |

→ 与 [Ch 7 `mmapsnoop`](./chapter-07-内存.md) 互补。

### `filelife`

找出 **寿命极短** 的文件（创建后很快删除）— 临时文件 I/O 优化。

```bash
sudo filelife-bpfcc
```

**场景：** 不必要的 `/tmp` 抖动、安装脚本垃圾。

---

## 7. 具体文件系统：ext4 / XFS

当问题沉到 **具体 FS 实现** 层：

### `ext4dist` / `xfsdist`

**延迟分布直方图** — ext4/XFS 内部常见操作（读、写、打开、fsync…）。

```bash
sudo ext4dist-bpfcc 10
sudo xfsdist-bpfcc 10
```

### `ext4slower` / `xfsslower`

打印该 FS 内慢于阈值的操作。

```bash
sudo ext4slower-bpfcc 10
sudo xfsslower-bpfcc 10
```

**拆解示例：**

```
cachestat  → 命中率高（读不是瓶颈）
ext4dist   → fsync 尾延迟极大
writeback  → 内存压力触发大量 flush
```

→ 下一步：应用是否 **过度 fsync**、挂载选项、`noatime`、或 [Ch 9 块层](./chapter-09-磁盘IO.md)。

---

## 8. 工具选型速查

| 症状 | 优先工具 |
|------|----------|
| 不知访问了哪些文件 | `opensnoop`、`filetop` |
| 逻辑 I/O 慢 | `fileslower` |
| 缓存是否够用 | `cachestat` |
| 写延迟尖刺 | `writeback`、`ext4dist`/`xfsdist` |
| 预读浪费 | `readahead` |
| 路径查找慢 | `dcsnoop`、`dcstat` |
| mmap 文件 | `mmapfiles`、`fmapfault` |
| 临时文件风暴 | `filelife` |
| FS 内部慢操作 | `ext4slower` / `xfsslower` |

---

## 9. 与 Ch 7 / Ch 9 的衔接

| 层 | 章 | 关键工具 |
|----|-----|----------|
| 内存回收挤占 cache | Ch 7 | `drsnoop`、`vmscan` |
| **文件系统 / 页缓存** | **Ch 8** | `cachestat`、`fileslower` |
| 块设备 / 磁盘 | Ch 9 | `biolatency`、`biosnoop` |

**下钻顺序：** `fileslower`（逻辑慢）→ `cachestat`（是否 cache miss）→ `ext4dist`（FS 层）→ `biolatency`（盘）。

---

## 10. HFT 读者 Takeaway

1. **默认 ⚪ 跳过** — 低延迟交易不应在热路径同步读盘；若 `opensnoop` 在 tick 路径上频繁出现，即 **架构 red flag**。
2. **incident 三板斧：** `filetop`（谁在写）→ `fileslower`（是否同步慢 I/O）→ `cachestat`（是否内存/cache 问题）。
3. **日志与配置** 是 HFT 机上最常见的 FS 噪声 — `opensnoop` 查意外路径，`filelife` 查临时文件。
4. **`mmap` 行情/历史数据** 用 `mmapfiles`/`fmapfault` + [Ch 7 `faults`](./chapter-07-内存.md) — 冷启动 vs 稳态分开看。
5. **`strace` 勿上生产热路径** — 用 BCC 聚合工具替代。
6. 缓存与内存争用：[Ch 7](./chapter-07-内存.md)；盘本身：[Ch 9](./chapter-09-磁盘IO.md)。

---

## 相关章节

- 上一章：[chapter-07-内存.md](./chapter-07-内存.md)
- 下一章：[chapter-09-磁盘IO.md](./chapter-09-磁盘IO.md)
- VFS 教学 OS：[01-30days-os day-18-dir](../09-system-low-level-hands-on/01-30days-os/day-18-dir/)
- SysPerf 文件系统：[chapter-08-file-systems](../02-Systems-Performance-2nd/chapter-08-file-systems/)（若存在）
- 方法论：[chapter-03-性能分析.md](./chapter-03-性能分析.md)
