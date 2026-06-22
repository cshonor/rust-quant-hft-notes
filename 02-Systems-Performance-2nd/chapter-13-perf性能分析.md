# Ch 13 perf 性能分析 · perf

> **Systems Performance 2nd** · Brendan Gregg · **精读**

> 本章定位：**Linux 官方标准剖析器 `perf(1)` 全书参考** — 贯穿 Ch 5–10 的 CPU/内存/磁盘/网络分析。Ch 4 选了 perf；本章讲 **事件源、子命令、栈回溯、火焰图流水线**。Ch 15 BPF 可编程更强；**perf 仍是 HFT 裸机第一工具**（零代码、PMC、官方支持）。

---

## 大白话 · 本章就五件事

> **perf = 计数（stat）+ 采样（record）+ 追踪（trace），接硬件到用户态。**

**① 子命令分工：`stat` 数事件，`record` 采栈，`report/script` 读结果，`trace` 跟 syscall。**

- 生产危机：**先 `perf stat` / `perf top`** — 低开销；深入再短 **`perf record -g`**。

**② 四类事件源：Hardware / Software / Tracepoint / Probe。**

- **PMC**：cycles、IPC、cache miss — Ch 6 周期分析落地。
- **tracepoint**：syscall、block I/O；**kprobe/uprobe/USDT**：动态插桩。

**③ `perf stat` — 计数，极低开销。**

- 全局或 `-p PID`；`-I 1000` 间隔统计；算 **IPC**、看 branch-miss。

**④ `perf record` + `report`/`script` — 采样剖析 → 火焰图。**

- **99 Hz** 常见（减与 timer 锁频）；**`-g`** 采调用栈；**`-F` 频率采样** vs **`-c` 周期/event 计数触发**。
- `perf script | stackcollapse | flamegraph.pl` — **火焰图必备管道**。

**⑤ 栈与符号：fp、`-g`、debuginfo — 否则 Ch 5 Gotchas 全中。**

- Release 构建 **`-g -fno-omit-frame-pointer`**；Java 要 perf-map-agent。

下面按原书 13.1–13.12 展开。

---

## 13.1–13.2 子命令概述与单行命令

### perf 工具集架构

```
perf
├── stat      事件计数（低开销）
├── record    采样 → perf.data
├── report    交互/文本汇总热点
├── script    逐行样本 → 火焰图输入
├── top       实时 TUI 热点
├── trace     syscall 追踪（低开销 strace）
├── list      列出可用 events
├── probe     创建 kprobe/uprobe
└── ...       mem, sched, lock, stat 等扩展
```

**版本：** `perf` 需 **匹配运行内核**（`linux-tools-$(uname -r)`）— Ch 4 危机工具清单。

### 单行命令集锦（HFT 常备）

```bash
# --- 快速健康 ---
perf stat -e cycles,instructions,cache-misses,branch-misses -- sleep 1
perf stat -p $(pidof strategy) -- sleep 5

# --- IPC + 缺页 ---
perf stat -e cycles,instructions,page-faults,major-faults -p $(pidof strategy) -- sleep 10

# --- CPU 热点（短采，限时长）---
perf record -F 99 -g -p $(pidof strategy) -- sleep 30
perf report --stdio | head -40

# --- 火焰图管道（需 FlameGraph 仓库）---
perf record -F 99 -g -p $(pidof strategy) -- sleep 60
perf script | stackcollapse-perf.pl | flamegraph.pl > strategy.svg

# --- 实时 top ---
perf top -p $(pidof strategy)

# --- syscall 追踪（开发/debug，生产限时长）---
perf trace -p $(pidof strategy) -- sleep 5

# --- 列出事件 ---
perf list | grep -E 'cache|fault|sched'
```

**生产原则：** `stat`/`top` 优先；`record` **限 PID + 限时长**；`trace` 比 strace 轻但仍非零开销。

→ Ch 4 [perf 定位](./chapter-04-观测工具.md) · Ch 12 [压测时 profile](./chapter-12-基准测试.md)

---

## 13.3–13.7 perf 事件源

### 硬件事件（Hardware Events / PMCs）

来自 CPU **性能监控计数器** — Ch 6 周期分析基础。

| 事件（示例） | 含义 |
|--------------|------|
| `cycles` | CPU 周期 |
| `instructions` |  retired 指令 → **IPC** |
| `cache-references` / `cache-misses` | cache 行为 |
| `L1-dcache-load-misses` | L1 数据 miss |
| `LLC-load-misses` | 末级 cache miss |
| `branch-misses` | 分支预测失败 |
| `stalled-cycles-frontend/backend` | 流水线停滞 |

```bash
perf stat -e cycles,instructions,cache-misses,LLC-load-misses ./strategy
```

**频率采样（Frequency Sampling）：**

- `perf record -F 99` — 约每秒 99 次样本（**非** 固定每 N 周期）。
- 优点：样本量随 CPU 活动自适应；**99 Hz** 减与 OS timer 拍频共振。
- 对比：`perf record -c 1000000 -e cycles` — 每 100 万周期采一次（event-based）。

**HFT：** 优化 order book 前后各跑 **`perf stat` IPC + LLC-misses** — 比凭感觉改结构可靠。

### 软件事件（Software Events）

内核维护的计数 — 无需特定 PMC。

| 事件 | 含义 |
|------|------|
| `page-faults` / `minor-faults` / `major-faults` | 缺页 |
| `context-switches` | 上下文切换 |
| `cpu-migrations` | 线程迁核 |
| `emulation-faults` | 等 |

```bash
perf stat -e page-faults,context-switches,cpu-migrations -p $(pidof strategy) -- sleep 10
```

→ Ch 7 [缺页火焰图](./chapter-07-内存.md#75-观测工具)

### 追踪点事件（Tracepoint Events）

内核 **静态** 观测点 — 稳定 ABI。

| 类 | 例子 |
|----|------|
| syscalls | `syscalls:sys_enter_read` |
| sched | `sched:sched_switch` |
| block | `block:block_rq_issue/complete` |
| kmem | `kmem:kmalloc` |

```bash
perf list 'syscalls:*' | head
perf record -e 'syscalls:sys_enter_write' -a -- sleep 5
```

**与 Ftrace：** tracepoint 是 Ftrace 子集；perf 可 **采样或计数** tracepoint — Ch 14 更偏 Ftrace 专精。

### 探针事件（Probe Events）

| 类型 | 作用 | 稳定性 |
|------|------|--------|
| **kprobes** | 内核任意函数动态插桩 | 内核版本变可能断 |
| **uprobes** | 用户态函数插桩 | 需符号 |
| **USDT** | 用户静态探针（如 libc、MySQL） | 应用需编译支持 |

```bash
# 创建 uprobe（示例）
perf probe -x /path/strategy 'decode_entry'
perf record -e probe_strategy:decode_entry -p PID -- sleep 10
```

**HFT：** 热路径函数 uprobe **有开销** — 开发/短采；生产优先 **99Hz 采样** 或 USDT span。

→ Ch 15 [BPF 可编程探针](./chapter-15-BPF技术.md)

---

## 13.8 `perf stat` — 事件计数

### 用途与特点

| 特点 | 说明 |
|------|------|
| **Counting** | 非采样 — 统计事件 **总次数** |
| **低开销** | 适合生产长时间跑 |
| **范围** | 全局 `-a` 或进程 `-p PID` |

### 高级选项

| 选项 | 作用 |
|------|------|
| `-e EVENT1,EVENT2` | 指定事件 |
| `-I 1000` | **每 1000ms 间隔** 打印一行 — 看趋势 |
| `-A` / `--no-aggr` | **每 CPU** 分开 — 负载均衡 |
| `--filter` | 内核/用户过滤 `u`/`k` |
| `-d` | 详细 stat（更多默认事件） |
| `-r 5` | **重复 N 次** — 看方差 |

```bash
# 每 CPU 每秒 IPC 趋势
perf stat -e cycles,instructions -I 1000 -a -- sleep 5

# 仅用户态
perf stat -e cycles,instructions -u -p $(pidof strategy) -- sleep 10
```

**Shadow Statistics：** 某些环境下 perf 用 **影子计数** 减干扰 — 详见 `man perf-stat`；理解「数字从哪来」即可。

**HFT 验收：** 绑核/调优前后 **`perf stat` 固定事件集** — 存档对比。

---

## 13.9 `perf record` — 剖析采样

### 工作原理

```
定时/事件触发 → 采当前 PC + 栈（若 -g）
    → 写入 perf.data（含符号表索引）
```

| 选项 | 含义 |
|------|------|
| `-F 99` | 99 Hz 频率采样 |
| `-c N -e cycles` | 每 N 周期采一次 |
| `-g` | **调用栈**（call graph） |
| `--call-graph fp` | 帧指针 unwinding（推荐，需 -fno-omit-frame-pointer） |
| `--call-graph dwarf` | debuginfo 栈 — 准但慢、体积大 |
| `-p PID` | 单进程 |
| `-a` | 全系统 |
| `-e EVENT` | 按事件采（如 page-faults） |
| `-- sleep N` | 采 N 秒 |

```bash
perf record -F 99 -g --call-graph fp -p $(pidof strategy) -- sleep 30
# 或全系统 crisis
perf record -F 99 -g -a -- sleep 10
```

### Stack Walking（栈回溯）配置

| 方法 | 要求 | HFT 推荐 |
|------|------|----------|
| **fp（帧指针）** | `-fno-omit-frame-pointer` | **Release 保留 fp** |
| **dwarf** | `-g` debuginfo | 调试构建 |
| **lbr** | 硬件 Last Branch Record | 部分 CPU |

**Ch 5 Gotchas 落地：**

- `[unknown]` → 装 debuginfo / 勿 strip
- 栈浅/断层 → 开 fp；减 `-O3` inline 或 dwarf

---

## 13.10 `perf report` 与 `perf script`

### `perf report`

解析 `perf.data` — TUI 或文本热点。

```bash
perf report --stdio --no-children | head -50
perf report --sort comm,dso,symbol    # 按进程/库/符号
perf report -g graph,0.5,caller        # 调用图
```

| 视图 | 用途 |
|------|------|
| **Overhead %** | 哪个符号占样本比最多 |
| **Children** | 含子调用累计 |
| **DSO** | 哪个 .so/.内核模块 |

### `perf script`

**逐行打印** 每个样本 — 火焰图 **预处理输入**。

```bash
perf script > out.perf
perf script | stackcollapse-perf.pl | flamegraph.pl > cpu.svg
```

**FlameGraph 仓库（Brendan Gregg）：**

```bash
# 克隆一次
git clone https://github.com/brendangregg/FlameGraph
export PATH=$PATH:/path/to/FlameGraph

perf script | stackcollapse-perf.pl | flamegraph.pl --title="strategy CPU" > strategy.svg
```

→ Ch 1/2/5/6 [火焰图读法](./chapter-02-方法论.md#210-统计与可视化)

**Off-CPU：** `perf record` 默认采 **on-CPU**；off-CPU 用 BPF `offcputime`（Ch 5/15）— **CPU + Off-CPU 火焰图缺一不可**。

---

## 13.11 `perf trace` — 系统调用追踪

类似 **strace**，基于 perf 基础设施 — **通常更低开销**。

```bash
perf trace -p $(pidof strategy) -- sleep 5
perf trace -e open,read,write,mmap -- sleep 3
```

| vs strace | perf trace |
|-----------|------------|
| 经典、功能全 | 集成 perf 生态 |
| 开销常较大 | 相对轻 |
| 生产慎用 | **仍限时长** |

**HFT：** 发现热路径 unexpected `read`/`mmap` — 开发机 `perf trace` 5 秒定位 syscall 类型。

---

## 13.12 其他常用能力（延伸）

| 子命令 | 用途 |
|--------|------|
| `perf mem` | 内存访问剖析 |
| `perf sched` | 调度延迟、迁移 |
| `perf lock` | 锁竞争 |
| `perf c2c` | **伪共享 / cache line** 争用（需支持） |
| `perf annotate` | 源码/汇编级热点 |

```bash
perf sched record -p $(pidof strategy) -- sleep 10
perf sched latency
```

**HFT 锁/伪共享：** `perf c2c record` 或 Ch 6 PMC + [04-Hennessy](../04-Computer-Architecture-6th/) — 争用严重时再开。

---

## 本章 Checklist

- [ ] `perf` 版本与 **运行内核匹配**
- [ ] 会用 **`perf stat`** 算 IPC、看 cache-miss
- [ ] 会 **`perf record -F 99 -g --call-graph fp -p PID`**
- [ ] 会从 **`perf script`** 生成 **CPU 火焰图**
- [ ] Release 构建保留 **符号 + 帧指针**（Ch 5）
- [ ] 知道 **on-CPU perf** vs **off-CPU BPF** 分工
- [ ] 生产：**stat/top 优先**，record **限时长**

---

## HFT 精读捷径（Ch 13 在路线中的位置）

```
Ch 4  观测工具选型
Ch 5–10  各资源章「perf 能做什么」
Ch 12  压测时必须 profile
Ch 13  perf（本章：官方剖析器实操）
  → Ch 15 BPF（可编程、off-CPU、runqlat）
  → 03-BPF 专书
  → 11-HFT ch10 延迟与回归
```

**本章最小行动集：**

1. 裸机确认 **`perf --version`** 与 **`uname -r`** 匹配。
2. 对 strategy 跑 **`perf stat -e cycles,instructions,cache-misses -- sleep 5`** — 记 IPC。
3. **`perf record -F 99 -g -p PID -- sleep 30`** → 火焰图一张。
4. 检查二进制：**`-g -fno-omit-frame-pointer`**，`perf report` 无大片 `[unknown]`。

**Gregg 本章金句（HFT 版）：**

> **`perf` 是 Linux 性能分析的默认答案** — `stat` 数清楚，`record` 采明白，**script 画火焰图**。  
> 没有栈和符号的 profile **等于没 profile** — 编译时就要为 perf 留后路。

---

## 相关章节

- 上一章：[chapter-12-基准测试.md](./chapter-12-基准测试.md)
- 下一章：[chapter-14-Ftrace跟踪.md](./chapter-14-Ftrace跟踪.md)
- 观测地图：[chapter-04-观测工具.md](./chapter-04-观测工具.md)
- CPU / PMC：[chapter-06-中央处理器.md](./chapter-06-中央处理器.md)
- 应用剖析：[chapter-05-应用程序.md](./chapter-05-应用程序.md)
- 缺页：[chapter-07-内存.md](./chapter-07-内存.md)
- BPF 互补：[chapter-15-BPF技术.md](./chapter-15-BPF技术.md)
- 附录 C bpftrace：[appendix-C-bpftrace单行命令.md](./appendix-C-bpftrace单行命令.md)
- 全书目录：[OUTLINE.md](./OUTLINE.md)
