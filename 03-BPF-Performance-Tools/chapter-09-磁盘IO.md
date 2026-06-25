# Ch 9 磁盘 I/O · Disk I/O

> **BPF Performance Tools** · Brendan Gregg · **跳过 ⚪**

> 本章定位：**物理块 I/O 栈** — [Ch 8](./chapter-08-文件系统.md) 的逻辑 I/O 在 cache miss 或必须落盘时，下沉为对 **块设备** 的请求。磁盘/SSD/NAS 比 CPU/内存慢 **数量级**，常是系统级瓶颈；BPF 在 **低开销** 下给出 **延迟直方图、逐 I/O 明细、发起栈**。  
> **HFT：** 交易热路径 **不应触盘**；本章 **⚪ 默认跳过**，用于 **日志盘打满、swap 误开、共置机后台 flush、NVMe 健康排查** 等。与 [Ch 3 `biolatency`](./chapter-03-性能分析.md) 清单衔接。  
> **上一章：** [chapter-08-文件系统.md](./chapter-08-文件系统.md) · **下一章：** [chapter-10-网络.md](./chapter-10-网络.md)

---

## 1. 本章要回答的问题

| 传统工具局限 | BPF 补什么 |
|--------------|------------|
| `iostat` 只有 **平均值** | **`biolatency`** 直方图 + 长尾 |
| `blktrace` **开销大、日志海量** | **`biosnoop`** 可控采样、内核聚合 |
| 不知 **谁** 在打盘 | **`biotop`** |
| 不知 **哪段内核/应用栈** 发起 I/O | **`biostacks`** |

```
Ch 8 逻辑 I/O（cachestat / fileslower）
        ↓ cache miss / fsync / swap
块层 Block Layer（biolatency / biosnoop / biostacks）
        ↓
I/O 调度器 mq-deadline / Kyber / BFQ（iosched）
        ↓
SCSI / NVMe 驱动（scsilatency / nvmelatency）
        ↓
设备
```

---

## 2. 磁盘 I/O 基础与块 I/O 栈

### 块 I/O 栈 (Block I/O Stack)

数据向下传递的典型路径：

```
文件系统 (ext4/xfs…)
    → 块设备接口
    → 卷管理 / LVM（可选）
    → device mapper（可选）
    → 块层 + I/O 调度器
    → HBA / SCSI / NVMe 驱动
    → 磁盘 / SSD / 阵列 / 网络存储
```

**HFT 共置机：** 系统盘写日志、数据盘 mmap 冷读、**swap 换出** 都会出现在块层 — 即使策略进程「不读写文件」。

### I/O 调度器 (Linux 5.0+)

| 调度器 | 特点 |
|--------|------|
| **mq-deadline** | 多队列默认常见；读/写 deadline |
| **Kyber** | 面向低延迟 SSD 的简化 mq 调度 |
| **BFQ** | 按进程公平，偏交互/桌面 |
| **none** | NVMe 上常见 — 软件调度最小化 |

**Multi-queue (blk-mq)：** 现代内核与 NVMe 队列深度匹配，替代旧单队列 CFQ 时代。

### 时间指标拆解

| 术语 | 含义 |
|------|------|
| **Wait Time** | 请求在 **OS/调度队列** 中排队等待 |
| **Service Time** | **设备实际处理** 时间 |
| **Request Time** | Wait + Service — **应用感知** 的块 I/O 时间 |

**`biosnoop`** 区分 **`QUE(ms)`**（排队）与 **`LAT(ms)`**（总延迟）— 判断 **盘慢** vs **队列拥塞**。

→ SysPerf 磁盘章：[chapter-09-disks](../02-Systems-Performance-2nd/chapter-09-disks/)

---

## 3. 传统磁盘分析工具

### `iostat`

```bash
iostat -dxz 1
```

| 字段 | 关注 |
|------|------|
| `rkB/s` / `wkB/s` | 吞吐 |
| `%util` | 设备忙碌程度（SSD 上勿绝对化） |
| **`await`** | **平均请求时间**（含排队+服务） |
| `r_await` / `w_await` | 读/写分项 |

**局限：** **均值掩盖长尾** — 双峰分布（设备 cache hit vs miss）在平均值里「看起来还行」。

### `perf` 与 `blktrace`

| 工具 | 特点 |
|------|------|
| `perf trace` block 事件 | 可追踪 `block_rq_*` |
| **`blktrace`** | 极详细，**busy 系统上开销与日志量巨大** |

**BPF 定位：** 介于 `iostat`（太粗）与 `blktrace`（太重）之间。

---

## 4. 基础延迟与实时观测

### `biolatency` — 块 I/O 延迟直方图 🔴

在内核按延迟桶 **聚合** 块 I/O — [Ch 3](./chapter-03-性能分析.md) 清单核心工具。

```bash
sudo biolatency-bpfcc -D 10      # 每 10s 打印直方图
sudo biolatency-bpfcc -F 10      # 按 I/O 标志分类（同步写、预读等）
```

| 直方图形态 | 解读 |
|------------|------|
| **双峰** | 部分 hit 设备/控制器 cache，部分走介质 |
| **右尾极长** | 长尾 outlier — HFT 共置机 P99 抖动线索 |
| 整体右移 | 盘饱和、调度拥塞、或网络存储故障 |

**HFT：** 热路径不应常触发；incident 时与 **`cachestat`**（Ch 8）对照 — miss 多 → 块层必忙。

### `biosnoop`

**逐行** 打印每次块 I/O：PID、大小、**QUE(ms)**、**LAT(ms)** 等 — 像「磁盘 tcpdump」。

```bash
sudo biosnoop-bpfcc
sudo biosnoop-bpfcc -d sda
```

| 对比 | 用途 |
|------|------|
| `QUE` 大、`LAT` 更大 | 排队 + 设备都慢 |
| `QUE` 大、`LAT`≈`QUE` | **OS 队列拥塞** 为主 |
| 低频精查 | 适合；高频勿长期开 |

### `biotop`

定期刷新 **块 I/O 流量最大** 的进程 — 块层版 `top` / `filetop`。

```bash
sudo biotop-bpfcc
```

**场景：** 谁在打满磁盘 — 日志进程、swap、未知后台任务。

---

## 5. I/O 模式与尺寸特征

### `bitesize`

按进程统计 I/O **块大小直方图** — 优化应用 buffer/块对齐。

```bash
sudo bitesize-bpfcc 10
```

| 模式 | 块大小倾向 |
|------|------------|
| 顺序大吞吐 | 大块 |
| 随机小 I/O | 小块 — SSD 仍怕过多 random write |

### `biopattern`

识别 **随机 vs 顺序** 访问百分比。

```bash
sudo biopattern-bpfcc 10
```

**场景：** 数据库/日志是顺序写还是 random read。

### `seeksize`

**寻道距离**（扇区）分布 — 主要为 **HDD** 设计；SSD 上参考意义下降。

```bash
sudo seeksize-bpfcc
```

---

## 6. 深层排障：栈、错误与驱动层

### `biostacks` — 发起 I/O 的调用栈 🔴

块 I/O 延迟 + **发起该 I/O 时的内核/用户栈** — 排障「谁在写盘」神器。

```bash
sudo biostacks-bpfcc 10
sudo biostacks-bpfcc -p $(pidof myapp)
```

| 典型栈顶 | 含义 |
|----------|------|
| `journal_submit_commit_record` | 文件系统日志 |
| `swap_writepage` | **Swap 换出** — HFT 配置事故 |
| `zfs_*` / `btrfs_*` | 特定 FS 后台 |
| 应用 `write` | 业务同步写盘 |

**与 Ch 8：** `fileslower` 见逻辑慢 → `biostacks` 见 **块层 + 栈**。

### `bioerr`

块设备 **I/O 错误** 时打印详情（错误码、设备）— 静默坏盘/链路问题。

```bash
sudo bioerr-bpfcc
```

### `iosched`

测量请求在 **I/O 调度器** 队列中的等待延迟（blk-mq 时代仍有用）。

```bash
sudo iosched-bpfcc
```

**解读：** `biolatency` 总延迟高 + `iosched` 排队高 → **软件队列** 瓶颈。

### `scsilatency` / `scsiresult`

| 工具 | 作用 |
|------|------|
| `scsilatency` | SCSI 命令延迟分布 |
| `scsiresult` | SCSI 返回状态（`DID_OK`、`DID_BAD_TARGET`…） |

**场景：** SAN、HBA、多路径存储。

### `nvmelatency`

**NVMe 驱动层** 命令延迟（如 `nvme_cmd_read`）— 分离 **纯设备延迟** vs OS 上层开销。

```bash
sudo nvmelatency-bpfcc
```

**HFT 共置机：** 系统盘多为 NVMe — 区分「盘本身慢」还是「上层 flush 堆叠」。

---

## 7. 工具选型速查

| 症状 | 优先工具 |
|------|----------|
| 磁盘慢但不知分布 | **`biolatency`** |
| 谁在读写的最多 | `biotop` |
| 单次 I/O 明细 | `biosnoop`（短窗口） |
| 疯狂写盘不知来源 | **`biostacks`** |
| 块大小不合理 | `bitesize` |
| random vs sequential | `biopattern` |
| 调度队列拥塞 | `iosched` + `biosnoop` QUE |
| NVMe 设备层 | `nvmelatency` |
| SCSI/SAN | `scsilatency`、`scsiresult` |
| I/O 硬件错误 | `bioerr` |
| 逻辑层先查 | [Ch 8 `cachestat`/`fileslower`](./chapter-08-文件系统.md) |

---

## 8. 与 Ch 8 / Ch 7 的下钻链

```
应用慢？
  ├─ Ch 8 fileslower / cachestat  → 逻辑 I/O / 缓存
  ├─ Ch 7 drsnoop / swapin        → 回收 / swap 导致写盘
  └─ Ch 9 biolatency / biostacks    → 块层延迟与发起栈
```

**Gregg 经典组合：**

```
cachestat  命中低  →  预期 biolatency 右移
biolatency 长尾   →  biosnoop 抓 outlier
biostacks          →  定位 journal / swap / 应用 write
```

---

## 9. BPF / bpftrace One-Liners（示意）

```bash
# 块 I/O 延迟直方图（优先用 biolatency-bpfcc）
# bpftrace -e 'tracepoint:block:block_rq_complete { @us = hist(((args->sector) * 512)); }'

# 按 comm 计数 block 完成事件（粗筛）
bpftrace -e 'tracepoint:block:block_rq_complete { @[comm] = count(); }'
```

→ 生产固定用 BCC 工具；bpftrace 验证 tracepoint 名与内核版本。

---

## 10. HFT 读者 Takeaway

1. **热路径零块 I/O** — 若 `biotop`/`biostacks` 在交易时段有策略 PID，即严重 red flag。
2. **`biolatency` 是 Ch 3 清单成员** — 比 `iostat await` 更看 **长尾**；incident 10–30s 短采即可。
3. **`biostacks` + swap 栈** — 延迟尖刺且 CPU/网正常时，查 **swap 是否误开**（[Ch 7 `swapin`](./chapter-07-内存.md)）。
4. **共置机日志盘** — `biotop` 找进程 → `biostacks` 找 `journal`/`writeback` 栈。
5. **NVMe 机器** 用 `nvmelatency` 分离设备 vs OS；HDD 场景才重点 `seeksize`。
6. 网络与存储争用：[Ch 10 网络](./chapter-10-网络.md) — HFT 主战场在网，非盘。

---

## 相关章节

- 上一章：[chapter-08-文件系统.md](./chapter-08-文件系统.md)
- 下一章：[chapter-10-网络.md](./chapter-10-网络.md)
- 内存/swap：[chapter-07-内存.md](./chapter-07-内存.md)
- 检查清单：[chapter-03-性能分析.md](./chapter-03-性能分析.md)
- SysPerf 磁盘：[chapter-09-disks](../02-Systems-Performance-2nd/chapter-09-disks/)
- CSAPP I/O：[chapter-10-system-io](../01-CSAPP-3rd/chapter-10-system-io/)
