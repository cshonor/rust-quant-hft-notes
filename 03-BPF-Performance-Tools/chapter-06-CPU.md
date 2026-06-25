# Ch 6 CPU · CPUs

> **BPF Performance Tools** · Brendan Gregg · **精读 🔴**

> 本章定位：**Part II 开篇** — CPU 执行所有代码，通常是性能分析的 **第一个切入点**。回顾 CPU 模式/调度/缓存基础与传统工具后，重点介绍 **CPU 与调度器相关的 BCC/bpftrace 工具**。  
> **HFT：** 共置交易机上 **绑核 + 专用核** 场景下，`runqlat` 应接近 0；若 P99 抖动却 `top` 不忙，用 **`offcputime`** 找阻塞栈、**`profile`** 找在核热点 — 与 [Ch 3 清单](./chapter-03-性能分析.md) 直接衔接。  
> **上一章：** [chapter-05-bpftrace.md](./chapter-05-bpftrace.md) · **下一章：** [chapter-07-内存.md](./chapter-07-内存.md)

---

## 1. 本章要回答的两个问题

| 问题 | 工具族 | 视角 |
|------|--------|------|
| **CPU 在忙什么？** | `profile`、火焰图、`cpudist`、`syscount` | **On-CPU** — 在核上执行什么代码 |
| **线程为什么得不到 CPU？** | `runqlat`、`runqslower`、`runqlen` | **调度饱和度** — 排队多久才跑上核 |
| **线程不跑时在等什么？** | `offcputime` | **Off-CPU** — 睡眠/阻塞栈与等待时间 |

```
         On-CPU                    Off-CPU
    profile / cpudist          offcputime
    火焰图 / llcstat              |
         \                       /
          \   runqlat（就绪→上核）/
           ----------------------
              调度器 / 运行队列
```

---

## 2. CPU 基础知识 (Background)

### CPU 模式

| 模式 | 说明 | 传统工具中的体现 |
|------|------|------------------|
| **用户态** | 应用代码 | `top` 的 `%us` |
| **内核态** | 系统调用、驱动、协议栈 | `%sy` |
| **空闲 / iowait / steal** | 等 I/O、虚拟化偷跑等 | `%id`、`%wa`、`%st` |

**HFT：** 策略热路径应 **大部分在用户态**；`%sy` 突增 → 查 syscall 风暴或内核网络栈（衔接 [Ch 10 网络](./chapter-10-网络.md)）。

### CPU 调度器与线程状态

调度器在 **任务（线程）** 之间分配 CPU 时间片：

| 状态 | 含义 | BPF 相关 |
|------|------|----------|
| **ON-CPU** | 正在某核上运行 | `profile`、`cpudist` |
| **RUNNABLE** | 就绪，在 **运行队列** 等 CPU | `runqlat`、`runqlen`、`runqslower` |
| **SLEEP** | 阻塞（I/O、锁、futex…） | `offcputime` |

→ 内核实现对照：[05-LKD Ch 4 调度](../05-Linux-Kernel-Development/00_Book_3rd_Notes/chapter-04-process-scheduling/)

### CPU 缓存与 TLB

现代负载常为 **内存/缓存密集型**，不单看 GHz：

| 层级 | 作用 |
|------|------|
| **L1 / L2** |  per-core，最快 |
| **L3 (LLC)** | 末级缓存，多核共享 |
| **TLB** | 虚拟地址 → 物理页表项缓存 |

**工具：** `perf` PMC、`llcstat`（BPF + 硬件计数）看 LLC 命中/未命中 — 与 [CSAPP Ch6 存储层次](../01-CSAPP-3rd/chapter-06-memory-hierarchy/) 对照。

→ SysPerf CPU 章：[chapter-06-cpus](../02-Systems-Performance-2nd/chapter-06-cpus/)

---

## 3. 传统 CPU 分析工具

**先传统、后 BPF** — [Ch 3 § Linux 60 秒](./chapter-03-性能分析.md) 已列；本章补充 CPU 专项：

### 系统状态与利用率

| 工具 | 看什么 |
|------|--------|
| `uptime` | load average — 可运行 + 不可中断任务压力 |
| `top` / `htop` | 整体 %us/%sy、 per-process CPU |
| `mpstat -P ALL 1` | **每核** 利用率 — 发现单核打满、不均衡 |
| `pidstat -p PID -u 1` | 单进程 CPU 随时间变化 |

```bash
mpstat -P ALL 1
pidstat -u -p $(pidof my_strategy) 1
```

### perf 与 PMC

| 用途 | 示例 |
|------|------|
| 采样剖析 | `perf record -F 99 -a -g -- sleep 30` |
| 硬件计数 | `perf stat -e cache-misses,cycles,instructions` |
| IPC | instructions / cycles — 低 IPC 常暗示缓存/分支问题 |

### CPU 火焰图

```
perf record -F 99 -a -g -- sleep 30
perf script | stackcollapse-perf.pl | flamegraph.pl > cpu.svg
```

**要点：** 采样频率常用 **49Hz / 99Hz** — 避免与内核 tick 锁步；宽度 = 该栈占样本比例。

→ 栈与火焰图原理：[Ch 2 § 火焰图](./chapter-02-技术背景.md) · BCC 等价：`profile-bpfcc`

---

## 4. BPF 相对传统工具的优势

| 盲区 | BPF 如何补 |
|------|------------|
| **极短命进程** | `top` 采样不到 → `execsnoop` |
| **运行队列等待** | `mpstat` 只见忙闲 → **`runqlat` 直方图** |
| **Off-CPU 原因** | `perf` 默认 on-CPU → **`offcputime`** |
| **按进程 LLC** | `perf stat` 粗粒度 → **`llcstat`** |

---

## 5. 进程与线程生命周期

### `execsnoop`

追踪 **新进程 exec** — 系统范围。

```bash
sudo execsnoop-bpfcc
```

| 场景 | 价值 |
|------|------|
| 短命 shell 循环、健康检查脚本 | CPU 被吃掉但 `top` 里一闪而过 |
| 异常 fork 风暴 | 看谁在不断拉起子进程 |

### `exitsnoop`

追踪 **进程退出**，含 **存活时长 (Age)**、退出码/信号。

```bash
sudo exitsnoop-bpfcc
```

**HFT：** 排查 watchdog 反复重启、子进程崩溃循环。

---

## 6. 调度器与饱和度

### `runqlat` — 运行队列延迟 🔴

测量：**线程进入 RUNNABLE → 实际在 CPU 上运行** 的等待时间分布。

```bash
sudo runqlat-bpfcc 10          # 每 10s 打印直方图
sudo runqlat-bpfcc -P 1 10     # 仅 CPU 1（绑核核对）
```

| 解读 | 含义 |
|------|------|
| 直方图右尾拉长 | CPU **饱和** — 就绪线程排队 |
| 绑核 dedicated 核接近 0 | 健康 |
| 突刺与行情峰值对齐 | 可能争抢同核、或邻居进程干扰 |

**Gregg 观点：** 排队 **时间 (latency)** 比排队 **长度 (length)** 更直接反映性能影响 — 但仍可用 `runqlen` 辅助。

### `runqlen`

**采样** 各 CPU 运行队列 **长度**（有多少线程在等）。

```bash
sudo runqlen-bpfcc 5
```

### `runqslower`

仅打印 **等待超过阈值** 的线程（如 >10ms）— 适合抓 **长尾**，避免海量输出。

```bash
sudo runqslower-bpfcc 10       # 10ms
```

**HFT runbook：** incident 时 **先 `runqlat` 10s** → 若右尾异常再 `runqslower` 抓具体 PID/栈。

---

## 7. CPU 使用时间与剖析 (On-CPU)

### `cpudist`

统计线程每次 **被调度上 CPU 后连续运行多久** 的分布（时间片长度分布）。

```bash
sudo cpudist-bpfcc -p $(pidof myapp) 10
```

与 `runqlat` 互补：一个看 **等 CPU 多久**，一个看 **上 CPU 后跑多久**。

### `cpufreq`

采样 CPU **实际运行频率** — 是否因省电策略降频。

```bash
sudo cpufreq-bpfcc 5
```

**HFT 生产：** 交易机通常 **performance governor** + 关 C-states；若频率掉下去，延迟会莫名变差。

### `profile` — CPU 栈采样 🔴

按固定频率（如 **99Hz**）采样 **全栈**，统计次数 — 生成火焰图的输入。

```bash
sudo profile-bpfcc -F 99 30
sudo profile-bpfcc -F 99 -p $(pidof myapp) 30
```

| 参数 | 说明 |
|------|------|
| `-F` | 采样频率 Hz |
| `-p` | 仅某进程 |
| `-U` | 仅用户态栈 |

**与 `perf record`：** 同属 on-CPU 采样；BCC 版便于与书中其他 BCC 工具一致、脚本化。

### `syscount`（关联）

按 **系统调用类型** 计数 — 回答「CPU 时间是否耗在 syscall 上」。

```bash
sudo syscount-bpfcc -i 1
```

---

## 8. Off-CPU 时间 — `offcputime` 🔴

与 `profile` **完美互补**：

| | `profile` | `offcputime` |
|---|-----------|--------------|
| **采样时机** | 线程 **在 CPU 上** | 线程 **被切换下 CPU**（阻塞） |
| **回答** | 在算什么 | **在等什么**（I/O、锁、futex…） |
| **输出** | 栈频率 → 火焰图 | 栈 + **等待时间** 汇总 |

```bash
sudo offcputime-bpfcc -p $(pidof myapp) 30
```

**典型发现：** 热路径在等 `futex`、等 `epoll`、等磁盘 — 引导到 [Ch 7 内存](./chapter-07-内存.md) / [Ch 9 磁盘](./chapter-09-磁盘IO.md) / 应用锁分析。

**HFT：** P99 升高但 `profile` 无热点 → **优先 offcputime**（是否在等锁或内核 I/O）。

---

## 9. 中断与其他

### `softirqs` / `hardirqs`

测量处理 **软/硬中断** 的 **时间分布**（不仅是次数）— 网络、块设备高负载时内核态飙高的常见原因。

```bash
sudo hardirqs-bpfcc 5
sudo softirqs-bpfcc 5
```

### `smpcalls`

**SMP 跨核调用 (IPI)** 耗时 — 多核同步、TLB shootdown 等。

```bash
sudo smpcalls-bpfcc
```

### `llcstat`

利用 **硬件 PMC**，在内核汇总 **每进程 LLC 命中/未命中**。

```bash
sudo llcstat-bpfcc 5
```

**注意：** 需 PMU 可用；虚拟化环境可能受限。

---

## 10. BPF 单行命令 (One-Liners)

本章末尾示例 — 与 [Ch 5](./chapter-05-bpftrace.md)、[附录 A](./appendix-A-bpftrace单行命令.md) 衔接：

```bash
# 全系统 CPU 栈采样（bpftrace）
bpftrace -e 'profile:hz:99 { @[kstack] = count(); }'

# 上下文切换时的内核栈
bpftrace -e 'tracepoint:sched:sched_switch { @[kstack] = count(); }'

# 某 PID 的 on-CPU 用户栈
bpftrace -e 'profile:hz:99 /pid == 1234/ { @[ustack] = count(); }'

# runqlat 等价思路（教学用；生产直接用 runqlat-bpfcc）
# 见 man runqlat-bpfcc
```

**原则：** 固定场景用 **BCC 工具**（已优化、有 man）；**验证假设** 用 bpftrace 单行。

---

## 11. 工具选型速查

| 症状 | 优先工具 |
|------|----------|
| 整体 CPU 高 | `mpstat` → `profile` / 火焰图 |
| 延迟高但 CPU 不高 | `offcputime` |
| 怀疑调度/抢核 | `runqlat`、`runqslower` |
| 短命进程 | `execsnoop` |
| 单核打满 | `mpstat -P ALL` + `profile -C` |
| 缓存/IPC 差 | `perf stat`、`llcstat` |
| 中断风暴 | `hardirqs`、`softirqs` |
| syscall 过多 | `syscount` |

---

## 12. HFT 读者 Takeaway

1. **两个核心问题：** 在核忙什么（`profile`）vs 为什么拿不到核（`runqlat`）vs 不跑时在等什么（`offcputime`）。
2. **`runqlat` 是绑核健康度体温计** — dedicated 策略核右尾应极短；与 [SysPerf Ch6](../02-Systems-Performance-2nd/chapter-06-cpus/) 一致。
3. **火焰图频率 99Hz**，避免与 tick 对齐；热路径 profile 加 `-p` 降噪。
4. **Off-CPU 与 On-CPU 成对使用** — 只 profile 会漏掉「等锁/I/O」型延迟。
5. **`cpufreq` / governor** — 生产前 checklist，别在压测机以外的地方抄配置。
6. BPF 采集 **限时、限 PID、避开最低延迟核**（或仅在 incident 窗口启用）。

---

## 相关章节

- 上一章：[chapter-05-bpftrace.md](./chapter-05-bpftrace.md)
- 下一章：[chapter-07-内存.md](./chapter-07-内存.md)
- 检查清单：[chapter-03-性能分析.md](./chapter-03-性能分析.md)
- BCC 工具箱：[chapter-04-BCC.md](./chapter-04-BCC.md)
- SysPerf CPU：[chapter-06-cpus](../02-Systems-Performance-2nd/chapter-06-cpus/)
- SysPerf BPF 总览：[chapter-15-bpf](../02-Systems-Performance-2nd/chapter-15-bpf/)
- 体系结构/cache：[04-Hennessy](../04-Computer-Architecture-6th/) · [01-CSAPP Ch6](../01-CSAPP-3rd/chapter-06-memory-hierarchy/)
