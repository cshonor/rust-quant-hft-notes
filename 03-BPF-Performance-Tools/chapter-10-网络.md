# Ch 10 网络 · Networking

> **BPF Performance Tools** · Brendan Gregg · **精读 🔴**

> 本章定位：**全书 Part II 最厚的一章** — Linux 网络栈全路径 + **海量 BPF 工具**。eBPF 源于包过滤；相对 `tcpdump`，BPF 能把 **包/连接事件 ↔ PID ↔ 调用栈** 绑在一起。  
> **HFT：** 共置机 **内核网络栈** 仍是行情/风控/日志的主战场之一（未全量 DPDK 时）；**`tcpretrans`、`tcpconnect`、`tcplife`、`gethostlatency`** 是 Ch 3 runbook 核心。旁路路径见 [note-XDP与tc-BPF](./note-XDP与tc-BPF.md) · [14-DPDK](../14-DPDK-Low-Latency-Network/)。  
> **上一章：** [chapter-09-磁盘IO.md](./chapter-09-磁盘IO.md) · **下一章：** [chapter-11-安全.md](./chapter-11-安全.md)

---

## 1. 本章要回答的问题

| tcpdump / ss 的盲区 | BPF 补什么 |
|---------------------|------------|
| 看到包，不知 **哪个进程** 发的 | `tcpconnect`、`soconnect` + **PID/comm** |
| 只有线路统计 | **内核状态**：重传、SYN 队列、socket 缓冲 |
| 抓包 **高开销** | `tcplife`、`tcpretrans` **内核聚合** |
| 连接慢不知卡在哪 | `soconnlat`、`so1stbyte` + 栈 |

```
应用 syscall (socket/connect/send/recv)
        ↓
套接字层（sockstat / soconnect / socketio / sormem）
        ↓
TCP/UDP（tcpconnect / tcplife / tcpretrans / tcpsynbl）
        ↓
IP / DNS（gethostlatency / ipecn / superping）
        ↓
qdisc / skb / 驱动（qdisc-* / skbdrop / nettxlat / netsize）
        ↓
NIC  ·  旁路：DPDK / XDP → note-XDP
```

---

## 2. 网络基础知识 (Background)

### Linux 网络栈路径

```
应用程序
  → Socket API（用户态）
  → 传输层 TCP/UDP
  → 网络层 IP
  → qdisc（排队规则）
  → 网卡驱动 / NAPI
  → NIC
```

→ 协议语义：[12-TCP-IP](../12-TCP-IP-Illustrated-Vol1/) · 内核栈：[13-Rosen](../13-Linux-Kernel-Networking/) · Socket API：[11-UNP](../11-UNP-Vol1/) · 实战：[10-PNP](../10-Practical-Network-Programming/)

### 内核绕过 (Kernel Bypass)

| 技术 | 说明 |
|------|------|
| **DPDK** | 用户态 PMD 轮询 NIC — **绕过内核栈**，避免 per-packet 复制/ syscall |
| **XDP / tc-BPF** | 仍在内核，但在 **最早** 收包点执行 BPF — 见 [note-XDP与tc-BPF](./note-XDP与tc-BPF.md) |

**HFT 分工：**

```
热路径行情/下单  →  DPDK / 内核 bypass（14-DPDK）
共置辅助流量     →  内核栈 + 本章 BPF 观测
对照实验         →  同一机：BPF 看内核栈 vs DPDK 看用户态环
```

### TCP 机制（观测相关）

| 机制 | BPF 工具关联 |
|------|--------------|
| **SYN Backlog / Listen Backlog** | `tcpsynbl` — 队列满 → SYN 丢包 |
| **重传**（超时 / 快速重传） | **`tcpretrans`** |
| **发送/接收缓冲区** 动态调整 | `sormem`、`tcpwin` |
| **Nagle** | `tcpnagle` — 小 packet 延迟 |
| **TFO** (TCP Fast Open) | 连接延迟分析时区分 |

### 卸载与分段

| 技术 | 作用 |
|------|------|
| **TSO/GSO** | 大块 TCP 分段 offload |
| **GRO/LRO** | 接收合并 |
| **影响** | `netsize` 可见软件分段前后包大小分布 |

### 常见延迟指标

| 指标 | 含义 |
|------|------|
| DNS 解析 | `gethostlatency` |
| ICMP RTT | `superping`（比用户态 ping 少调度噪声） |
| TCP 连接建立 | `soconnlat`、`tcpconnect` 时间线 |
| 首字节 | **`so1stbyte`** |

---

## 3. 传统网络分析工具

| 工具 | 用途 |
|------|------|
| **`ss -tinap`** | **首选** socket 统计 — 状态、重传、RTT、cwnd 等 |
| `ip -s link` | 网卡级计数、drop |
| `nstat` | 内核 SNMP 计数器 |
| `netstat` | 旧式，优先 `ss` |
| `sar -n DEV` | 接口吞吐 |
| **`nicstat`** | 网卡利用率、吞吐 |
| **`ethtool -S`** | 驱动/NIC 硬件计数（drop、fifo…） |
| **`tcpdump`** | 抓包 — **见线路，不见 PID/内核栈** |

```bash
ss -tinap
ip -s link show eth0
ethtool -S eth0 | grep -i drop
```

**抓包盲区（Gregg 强调）：**

| tcpdump 能 | tcpdump 不能 |
|------------|--------------|
| 线路上的包 | **哪个 PID** 发送 |
| 五元组 | **内核为何重传**（拥塞 vs 本地 drop） |
| pcap 文件 | **调用栈**、socket 缓冲满 |

→ 这正是 BPF 工具的价值。

---

## 4. 套接字层 (Socket API) 工具

### `sockstat` / `sofamily` / `soprotocol`

| 工具 | 统计 |
|------|------|
| `sockstat` | accept、connect 等 **事件频率** |
| `sofamily` | 地址族 IPv4/IPv6/UNIX… |
| `soprotocol` | TCP/UDP/… 协议分布 |

**用途：** **工作负载表征** — 连接型 vs 数据报、IPv6 占比。

### `soconnect` / `soaccept`

追踪 **connect / accept** — **IP、端口、PID、comm**。

```bash
sudo soconnect-bpfcc
sudo soaccept-bpfcc
```

**HFT：** 策略是否意外 **outbound 建连**（合规 API、DNS、telemetry）。

### `socketio` / `socksize`

按进程统计 socket **读写次数** 与 **字节数直方图**。

```bash
sudo socketio-bpfcc 5
sudo socksize-bpfcc
```

### `sormem`

**接收队列 (receive queue)** 大小直方图 — 缓冲溢出 → 内核 drop。

```bash
sudo sormem-bpfcc
```

### `soconnlat` / `so1stbyte`

| 工具 | 测量 |
|------|------|
| `soconnlat` | **连接建立** 延迟 + 栈 |
| `so1stbyte` | **首字节** 延迟 + 栈 |

**HFT：** 区分「TCP 握手慢」vs「连接后应用层首包慢」— 对 **网关/行情源** 接入排查极有用。

---

## 5. TCP 协议层工具

### `tcpconnect` / `tcpaccept`

在 **TCP 栈更深处** 挂载（比 socket 层更贴近协议状态）。

```bash
sudo tcpconnect-bpfcc
sudo tcpaccept-bpfcc
```

→ [Ch 3 BCC 清单](./chapter-03-性能分析.md) 含 `tcpconnect`。

### `tcplife` — 会话总结 🔴

连接 **建立时记录**，**关闭时一行总结**：

- 本地/远程 IP:端口  
- 收发总字节  
- **会话持续时间 (Lifespan)**  

```bash
sudo tcplife-bpfcc
```

| 优点 | 说明 |
|------|------|
| **低开销** | 不需抓包 |
| **HFT** | 看清某行情 TCP 会话活了多久、传了多少 — 异常长连/短连 |

### `tcptop`

TCP 版 **top** — 按 **发送/接收 Kbytes** 排序进程。

```bash
sudo tcptop-bpfcc
```

### `tcpretrans` — 重传追踪 🔴

追踪 **TCP 重传** — 地址、TCP 状态。

```bash
sudo tcpretrans-bpfcc
```

| 解读 | 含义 |
|------|------|
| 重传突增 | 拥塞、丢包、对端问题、**本机网卡 drop** |
| 与延迟尖刺同相 | 网络层首要嫌疑 |

**HFT runbook 三件套之一：** `runqlat` + `profile` + **`tcpretrans`**（Ch 3）。

### `tcpsynbl`

**SYN 积压队列** 直方图 — 警告 **SYN 丢包**（队列溢出）。

```bash
sudo tcpsynbl-bpfcc
```

**场景：** 接入层 accept 跟不上 SYN flood 或 legit 连接风暴。

### `tcpwin` / `tcpnagle`

| 工具 | 作用 |
|------|------|
| `tcpwin` | **拥塞窗口 cwnd** 变化 — 可导出 CSV 画拥塞控制 |
| `tcpnagle` | **Nagle 算法** 导致的发送延迟 |

**HFT：** 低延迟 socket 通常 **`TCP_NODELAY`** — `tcpnagle` 验证是否误开 Nagle。

---

## 6. UDP、DNS 与其他

### `udpconnect`

追踪 **UDP** “连接”/首次 sendto 目标。

```bash
sudo udpconnect-bpfcc
```

**HFT：** 组播/UDP 行情 — 与 [14-DPDK 组播笔记](../14-DPDK-Low-Latency-Network/01-Intro-Book/notes/chapter-05-组播行情接入.md) 对照。

### `gethostlatency`

追踪 **`getaddrinfo` 等 DNS 解析** 延迟。

```bash
sudo gethostlatency-bpfcc
```

**一针见血：** 慢在 **DNS** 还是 **网络 RTT** — 共置机偶发 `connect` 卡顿常见根因。

### `superping`

内核路径 **ICMP echo** 延迟 — 减少用户态 `ping` 的调度 jitter。

### `ipecn`

追踪 IPv4 **ECN (Explicit Congestion Notification)** 入站事件 — 拥塞信号是否到达。

---

## 7. 底层：qdisc / skb / 驱动

### `qdisc-*` 家族

针对 **fq、codel、cbq** 等排队规则测量 **包排队延迟**。

**场景：** 出口 bufferbloat、云主机 qdisc 配置不当。

### `netsize`

**GSO/GRO 前后** 设备层 send/recv **包大小直方图**。

### `nettxlat`

**网卡驱动 TX 队列** 延迟 — 包进 ring → 硬件发完。

**HFT：** 区分 **软件栈慢** vs **NIC 发送队列拥塞**（与 `ethtool -S` 配合）。

### `skbdrop`

`sk_buff` **异常丢弃** + **内核栈** — 丢包元凶。

```bash
sudo skbdrop-bpfcc
```

**极 valuable：** `ip -s` 见 drop 但不知原因 → `skbdrop` 给 **函数栈**。

### `skblife`

`sk_buff` 从分配到释放的 **生命周期耗时** — 包在栈里「呆太久」。

### `ieee80211scan`

WiFi 802.11 扫描耗时 — 数据中心 HFT 少见，笔记本调试可用。

---

## 8. 工具选型速查（HFT 优先）

| 症状 | 优先工具 |
|------|----------|
| 延迟尖刺、怀疑网络 | **`tcpretrans`** |
| 谁在用带宽 | `tcptop`、`socketio` |
| 意外 outbound 连接 | `tcpconnect`、`soconnect` |
| 连接/会话行为 | **`tcplife`** |
| 连接建立慢 | `soconnlat`、`tcpconnect` |
| 首包慢 | `so1stbyte` |
| DNS 拖慢 | **`gethostlatency`** |
| SYN 丢/满 | `tcpsynbl` |
| 接收缓冲溢出 | `sormem` |
| 内核 drop 不知因 | **`skbdrop`** |
| NIC TX 排队 | `nettxlat`、`ethtool -S` |
| 抓包替代（低开销） | `tcplife` + `tcpretrans` |

---

## 9. 与 DPDK / XDP 的分工

| 路径 | 观测手段 |
|------|----------|
| **内核栈 TCP/UDP** | 本章 BCC 工具 |
| **XDP 早丢弃/转发** | [note-XDP与tc-BPF](./note-XDP与tc-BPF.md) |
| **DPDK 用户态** | PMD stats、`testpmd`、应用计数 — [14-DPDK](../14-DPDK-Low-Latency-Network/) |

**勿混读：** DPDK 口上 **`tcpretrans` 可能无事件** — 工具针对内核 TCP 栈。

---

## 10. BPF / bpftrace One-Liners（示意）

```bash
# TCP 重传（生产用 tcpretrans-bpfcc）
# bpftrace -e 'kprobe:tcp_retransmit_skb { printf(...); }'

# 按 comm 统计 connect
bpftrace -e 'tracepoint:syscalls:sys_enter_connect { @[comm] = count(); }'

# 采样内核网络栈（短跑）
bpftrace -e 'kprobe:tcp_sendmsg { @[kstack] = count(); }'
```

→ [Ch 5 bpftrace](./chapter-05-bpftrace.md) · [附录 A](./appendix-A-bpftrace单行命令.md)

---

## 11. HFT 读者 Takeaway

1. **Ch 10 是共置机网络 incident 主章** — 与 Ch 6 CPU 并列精读。
2. **`tcpretrans` + `ss -ti`** — 重传是否发生、cwnd/RTT 是否异常；先 30s 短采。
3. **`tcpdump` 不能替代 BPF** — 无 PID/栈；高 pps 下抓包本身可能 **改变** 行为。
4. **`tcplife`** 低开销看清 **谁和谁谈了多久、传了多少** — 适合长跑监控（仍须限流）。
5. **`gethostlatency`** — 「偶发慢」先查 DNS，再 blame 网络。
6. **热路径已 DPDK 化** — 本章工具看 **管理面/辅助 TCP**；数据面用 14-DPDK + 应用指标。
7. **Nagle/offload** — `tcpnagle`、`ethtool -k` 与 socket 选项一并核对。
8. 延伸：**XDP/tc-BPF** 小包过滤 vs 全栈 bypass → [note-XDP与tc-BPF](./note-XDP与tc-BPF.md)。

---

## 相关章节

- 上一章：[chapter-09-磁盘IO.md](./chapter-09-磁盘IO.md)
- 下一章：[chapter-11-安全.md](./chapter-11-安全.md)
- XDP 延伸：[note-XDP与tc-BPF.md](./note-XDP与tc-BPF.md)
- 检查清单：[chapter-03-性能分析.md](./chapter-03-性能分析.md)
- SysPerf 网络：[chapter-10-network](../02-Systems-Performance-2nd/chapter-10-network/)
- DPDK：[14-DPDK-Low-Latency-Network](../14-DPDK-Low-Latency-Network/)
- CSAPP 网络：[chapter-11-network-programming](../01-CSAPP-3rd/chapter-11-network-programming/)
