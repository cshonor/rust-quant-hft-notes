# Ch 3 性能分析 · Performance Analysis

> **BPF Performance Tools** · Brendan Gregg · **选读 🟡**

> 本章定位：**性能分析速成课** — 不是 BPF 语法，而是 **目标、方法论、两套检查清单**（Linux 60 秒 + BCC 精选）。连接 [Ch 2 技术背景](./chapter-02-技术背景.md) 与 [Ch 4 BCC 专章](./chapter-04-BCC.md)。  
> **HFT：** 生产 incident 先 **业务指标 / 应用 span** 锁定嫌疑，再 **60 秒粗筛**，最后 **BCC/bpftrace 精准下钻** — 与 [SysPerf Ch 2 方法论](../02-Systems-Performance-2nd/chapter-02-methodologies/) 同序。  
> **上一章：** [chapter-02-技术背景.md](./chapter-02-技术背景.md) · **下一章：** [chapter-04-BCC.md](./chapter-04-BCC.md)

---

## 1. 性能分析的概述与目标

| 目标 | 说明 |
|------|------|
| **提高终端用户性能** | 延迟、吞吐、可用性 — HFT 即 tick→决策→发单全链路 |
| **降低运营成本** | 更少机器做同样 workload，或同样机器扛更高负载 |

**现实：** 往往 **同时存在多个** 性能问题 — 排查重点是找 **对延迟或成本影响最大** 的那一项，而非列表上第一个。

> **HFT：** Grafana / 应用 histogram 先回答「P99 涨在哪一段」；再决定开 `runqlat` 还是 `tcpretrans`，避免「BPF 全开」淹没信号。

---

## 2. 核心方法论

### 工作负载表征 (Workload Characterization)

回答 **系统在被什么驱动**：

| 问题 | 例子 |
|------|------|
| 谁引起负载？ | 哪个进程、哪条策略、哪类报文 |
| 为什么调用这段代码？ | 配置变更、新合约、retry 风暴 |
| 类型与吞吐？ | QPS、消息率、订单 cancel 比 |
| 随时间如何变？ | 开盘尖峰、roll 窗口 |

**Gregg 观点：** 最大收益常来自 **消除不必要的工作** — 比微优化一条热路径更猛。

→ [SysPerf 2.4 Workload vs Resource](../02-Systems-Performance-2nd/chapter-02-methodologies/notes/section-2.4-两种分析视角.md)

### 下钻分析 (Drill-Down Analysis)

从 **宏观指标** 一层层剥：

```
应用阻塞在文件系统
  → 阻塞在 write 路径
    → 阻塞在更新 access timestamp (atime)
      → 挂载选项 noatime 解决
```

**BPF 角色：** 每一层用 **不同工具** 验证假设 — `opensnoop` → `ext4slower` → `biolatency`，而非一次 attach 所有 probe。

### USE 方法 (USE Method)

对 **每个资源** 查三项：

| 字母 | 含义 | 问什么 |
|------|------|--------|
| **U** | Utilization 使用率 | 资源忙的时间比例？ |
| **S** | Saturation 饱和度 | 有排队/等待吗？（超额需求） |
| **E** | Errors 错误 | 硬件/驱动/协议错误？ |

**资源例：** CPU、内存、磁盘 I/O、网络、总线…

→ 本仓库展开：[SysPerf 附录 A USE](../02-Systems-Performance-2nd/appendix-A-USE方法Linux.md) · [Ch 2.3.1 走查](../02-Systems-Performance-2nd/chapter-02-methodologies/notes/section-2.3.1-时间尺度与排查走查.md)

---

## 3. Linux 60 秒检查清单（传统工具）

登录 **性能异常机器后前 60 秒** — **先跑这些，再开 BPF**。BPF 书仍强调传统工具 **粗筛方向**。

| # | 命令 | 看什么 |
|---|------|--------|
| 1 | `uptime` | load average — 整体资源压力 |
| 2 | `dmesg \| tail` | OOM、TCP 丢包、驱动错误 |
| 3 | `vmstat 1` | run queue、swap、user/sys CPU |
| 4 | `mpstat -P ALL 1` | **单核打满** vs 多核均衡 |
| 5 | `pidstat 1` | 哪个进程吃 CPU（随时间滚动） |
| 6 | `iostat -xz 1` | 磁盘 **`await`**（响应时间）、**`%util`** |
| 7 | `free -m` | **available**、buff/cache |
| 8 | `sar -n DEV 1` | 网卡吞吐是否顶满 |
| 9 | `sar -n TCP,ETCP 1` | TCP 连接率、**重传** |
| 10 | `top` | 综合核对 |

```bash
# 一键习惯：先 1–3，再按疑点加 4–9
uptime
dmesg | tail
vmstat 1
```

> **HFT 共置裸机：** 块设备 `iostat` 常 ⚪（无本地盘）；**8–9 网络** 与 **4–5 CPU** 通常是 60 秒重点。与 [SysPerf Ch 4 危机工具](../02-Systems-Performance-2nd/chapter-04-observability-tools/) 对照。

---

## 4. BCC 工具检查清单（BPF 深探）

传统工具给出 **方向** 后，用 BCC **精准打击**（包名可能是 `*-bpfcc` 或短名）：

### 进程与文件

| 工具 | 用途 |
|------|------|
| **`execsnoop`** | 短生命周期进程 — 疯狂 fork 的脚本/守护进程 |
| **`opensnoop`** | 文件打开 — 配置路径、ENOENT、日志位置 |

```bash
sudo execsnoop-bpfcc
sudo opensnoop-bpfcc
```

### 文件系统与磁盘 I/O

| 工具 | 用途 |
|------|------|
| **`ext4slower`** | ext4 慢操作（其他 fs 有 `xfs*`、`btrfs*` 等变体） |
| **`biolatency`** | 块 I/O **延迟直方图** — 长尾、多峰 |
| **`biosnoop`** | 每次 I/O 一行 — 谁、多大、多慢 |
| **`cachestat`** | 页缓存 hit/miss |

```bash
sudo biolatency-bpfcc -F -m 5 10
sudo cachestat-bpfcc 5
```

### 网络

| 工具 | 用途 |
|------|------|
| **`tcpconnect`** | 主动 outbound 连接 |
| **`tcpaccept`** | 被动 inbound 连接 |
| **`tcpretrans`** | **TCP 重传** — 丢包/拥塞信号 |

```bash
sudo tcpretrans-bpfcc
sudo tcpconnect-bpfcc
```

→ HFT 延伸：[note-XDP与tc-BPF.md](./note-XDP与tc-BPF.md) · [chapter-10-网络.md](./chapter-10-网络.md)

### CPU 调度与剖析

| 工具 | 用途 |
|------|------|
| **`runqlat`** | CPU **运行队列等待** 直方图 — 饱和度 |
| **`profile`** | ~49 Hz **栈采样** — CPU 热点火焰图原料 |

```bash
sudo runqlat-bpfcc 10
sudo profile-bpfcc -F 99 30   # 频率可调；99 避免与 tick 锁步
```

---

## 5. 两套清单如何串联

```
Incident / 延迟报警
        │
        ▼
  Workload 表征（业务指标：哪段、多大、何时）
        │
        ▼
  Linux 60 秒（uptime → vmstat → mpstat → sar …）
        │  粗方向：CPU？网？盘？内存？
        ▼
  USE 下钻（对嫌疑资源查 U/S/E）
        │
        ▼
  BCC 清单（runqlat / tcpretrans / biolatency / profile …）
        │
        ▼
  bpftrace ad hoc（验证单点假设）→ 附录 A
        │
        ▼
  修复 + 回归 baseline
```

**原则：** **先消除不必要工作** → **方法论定方向** → **传统工具 60 秒** → **BCC 聚合** → **bpftrace 补洞**。

---

## 6. HFT 读者 Takeaway

1. **Ch 3 不是可选哲学** — 没有方法论，BPF 只会产出 **更多数据**。
2. **60 秒 + BCC** 是 runbook 骨架 — 与 SysPerf **危机工具包** 合并成团队一页纸。
3. **直方图工具优先**（`runqlat`、`biolatency`）— 均值在 HFT 里几乎总是骗人。
4. **`profile` 找 CPU，`runqlat` 找排队，`tcpretrans` 找网** — 三条覆盖共置机 80% 内核侧嫌疑。
5. 定制 probe 留到 [Ch 5 bpftrace](./chapter-05-bpftrace.md) — 先熟练本章清单。

---

## 相关章节

- 上一章：[chapter-02-技术背景.md](./chapter-02-技术背景.md)
- 下一章：[chapter-04-BCC.md](./chapter-04-BCC.md)
- Ch 1 工具初探：[chapter-01-简介.md](./chapter-01-简介.md)
- SysPerf 方法论：[chapter-02-methodologies](../02-Systems-Performance-2nd/chapter-02-methodologies/)
- 附录 A bpftrace 单行：[appendix-A-bpftrace单行命令.md](./appendix-A-bpftrace单行命令.md)
