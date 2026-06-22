# Ch 10 网络 · Network

> **Systems Performance 2nd** · Brendan Gregg · **精读**

> 本章定位：**网络是分布式时代最常背锅的资源** — 问题可能在 DNS、TCP 握手、拥塞、内核队列、网卡，而非「带宽不够」。Ch 7–9 是内存/磁盘；本章是 **HFT 系统性能的主战场之一**（行情 ingress、发单 egress）。与 handbook `07`→`08`→`09`→`10-DPDK` 网络栈闭环 **并行互补**：本章偏 **内核标准栈 + 观测**；DPDK/XDP 偏旁路与早期 hook。

---

## 大白话 · 本章就五件事

> **网络慢，先拆延迟段，别先加带宽。**

**① 术语与 MTU：吞吐 ≠ 带宽；大包减开销。**

- **Throughput** = 实际数据传输率；**Bandwidth** = 链路上限。
- **MTU 1500** vs **Jumbo ~9000** — 减包头开销；共置/托管需全网一致。

**② 延迟是多段的 — 不只有一个 RTT。**

- DNS → Ping(ICMP) → **TCP 握手/重传** → **TTFB**（含服务器处理）→ RTT → 连接生命周期。
- HFT 发单：分解 **本地处理 + kernel + wire RTT + 对端**。

**③ 缓冲与积压：Bufferbloat + SYN 队列丢包。**

- 中间设备缓冲过大 → **bufferbloat** 增延迟。
- 监听队列/SYN backlog 满 → **丢 SYN** → 连接超时、重传风暴。

**④ 栈架构：TCP/UDP/QUIC + Linux 路径 + RSS/RPS + DPDK/XDP。**

- **CUBIC vs BBR**、Nagle、窗口、SACK、TFO；**TSO/GRO** 卸载。
- 极高 PPS：**RSS/RPS** 分核；极致：**DPDK** 旁路或 **XDP** 最早丢/改包。

**⑤ 工具与调优：`ss -tiepm`、tcplife、tcpretrans、iperf、sysctl、TCP_NODELAY。**

- 生产优先 **计数器 + BPF**；**tcpdump** 最后手段。
- Netflix 式 sysctl + 应用 **`TCP_NODELAY`** 降小包延迟。

下面按原书 10.1–10.8 展开。

---

## 10.1–10.3 核心概念与延迟指标

### 基础术语

| 术语 | 含义 | HFT |
|------|------|-----|
| **Throughput** | 实际达到的数据率 | 行情 MB/s、订单 msg/s |
| **Bandwidth** | 链路/网卡理论上限 | 10G/25G/100G 协商速率 |
| **Socket** | 网络 I/O 端点 | TCP 发单、UDP 组播 |
| **MTU** | 最大传输单元（以太网常 1500） | 分片增延迟 — 路径 MTU _discovery |
| **Jumbo Frames** | MTU ~9000 | 共置 LAN 常用；跨 WAN 慎用 |

→ [07-TCP/IP](../07-TCP-IP-Illustrated-Vol1/) · [08-UNP](../08-UNP-Vol1/)

### 多维度网络延迟

| 延迟类型 | 包含什么 | 测量 |
|----------|----------|------|
| **DNS** | 名称解析 | `dig` 计时 |
| **Ping (ICMP)** | 网络往返（非业务路径） | `ping` — 粗筛连通 |
| **Connection** | TCP 三次握手 + **SYN 重传** | `ss`、BPF `tcpconnect` |
| **TTFB** | 请求 → **首字节**（含服务端 think time） | 应用层 span |
| **RTT** | 往返时间 | `ss -ti` 内 `rtt` |
| **Connection lifetime** | 建立 → 关闭 | BPF **`tcplife`** |

**HFT 延迟分解示例（TCP 发单）：**

```
signal_ts → encode → send() → 内核 TCP → NIC → wire RTT → 交易所 ACK
              ↑           ↑                    ↑
           TTFB 本地    Connection/队列      RTT（共置仍非零）
```

→ Ch 2 [延迟分解](./chapter-02-方法论.md#27-延迟分析与分解) · [11-HFT ch10](../11-HFT-Low-Latency-Practice/chapter-10-延迟测量与基准压测.md)

### 缓冲与积压（Buffering & Backlog）

**Bufferbloat：**

- 交换机/路由器 **过大缓冲** → 排队延迟膨胀 — 吞吐高但 **latency 差**（与 HFT 目标相反）。
- 共置低延迟网络仍要关注 **交换机 buffer 配置**。

**TCP 连接积压：**

```
Client SYN → 内核 SYN queue / accept queue → listen socket backlog 满
                    ↓
              丢 SYN / 丢 ACK → 客户端重传 → 连接超时
```

| 队列 | 作用 |
|------|------|
| **SYN queue** | 半连接（SYN_RECV） |
| **Accept queue** | 已完成握手，等 `accept()` |

**HFT：** 行情 **UDP 组播** 无握手；**TCP 订单通道** 要调 `somaxconn`、`tcp_max_syn_backlog`，监控 **`ss -lnt`** 的 Send-Q/Recv-Q。

---

## 10.4 硬件与软件栈架构

### 协议层性能要点

**TCP：**

| 机制 | 作用 | HFT |
|------|------|-----|
| **滑动窗口** | 流量控制 | 窗口满 → 背压 |
| **慢启动 / 拥塞控制** | 防网络 collapse | **CUBIC**（默认）vs **BBR** |
| **SACK** | 选择性重传 | 减不必要重传 |
| **TFO** | TCP Fast Open | 减一轮 RTT（需两端支持） |
| **Nagle** | 小包合并 | 增延迟 — 发单常 **`TCP_NODELAY`** |
| **TIME_WAIT** | 关闭后状态 | 大量短连接 → 端口耗尽 — `tcp_tw_reuse` 等 |

**BBR vs CUBIC（Gregg 语境）：**

- **CUBIC**：丢包作拥塞信号 — 丢包环境下吞吐可能差。
- **BBR**：基于带宽/RTT 模型 — 某些场景 **吞吐可达 CUBIC 数倍**；但也曾引发 buffer 争议 — 生产需 A/B。

**UDP：**

- 无连接、无重传 — **组播行情**主路径；应用自管丢包/乱序。

**QUIC / HTTP3：**

- 用户态、0-RTT、多路复用 — Web/API；**tick 热路径**量化系统较少用，了解即可。

→ [09-Rosen](../09-Linux-Kernel-Networking/) · [03-BPF note-XDP](../03-BPF-Performance-Tools/note-XDP与tc-BPF.md)

### Linux 网络栈路径（简化）

```
NIC RX interrupt → softirq (NAPI poll) → netif_receive_skb
    → IP → TCP/UDP → socket receive queue → read()/recv()
TX: write() → TCP 分段 → qdisc → driver → NIC
```

| 组件 | 说明 |
|------|------|
| **Socket buffer** | `tcp_rmem` / `tcp_wmem` — 读写缓冲 |
| **qdisc** | 排队规则（pfifo_fast、fq、fq_codel…） |
| **TSO/GSO/GRO/LRO** | 分段/聚合 **卸载到网卡** — 降 CPU、改 latency 特征 |

**HFT：** `kernel`/`softirq` % 高 → 查 **RSS、RPS、中断亲和性**、是否该 **DPDK 旁路**。

→ [09 Rosen NAPI/softirq](../09-Linux-Kernel-Networking/) · [CROSS-MODULE-GUIDE §二](../CROSS-MODULE-GUIDE.md#二内核网络栈-vs-用户态旁路)

### CPU 扩展与内核绕过

| 技术 | 作用 |
|------|------|
| **RSS** | 网卡按 hash 把流分到多 RX 队列 |
| **RPS/RFS** | 软件把包分到不同 CPU 处理 |
| **IRQ affinity** | 中断绑核 — 与策略线程 **同 NUMA** |
| **DPDK** | 用户态 PMD 轮询 — **完全旁路**内核栈 |
| **XDP** | 驱动最早点 eBPF — 丢弃/转发/redirect |

```
标准栈：08 UNP socket → 09 Rosen 内核路径 → 本章观测
极致延迟：10-DPDK 01-Intro（组播） / 02-Advanced XDP·RDMA
```

→ [10-DPDK](../10-DPDK-Low-Latency-Network/) · [02-Advanced XDP note](../10-DPDK-Low-Latency-Network/02-Advanced-Book/notes/note-XDP与DPDK对照.md)

---

## 10.5 分析方法论

### USE 方法（Network Interface）

对 **每个 NIC**（及 bond/VLAN 逻辑口）：

| 字母 | 问什么 | 信号 |
|------|--------|------|
| **U** Utilization | 吞吐 / 协商带宽 | `sar -n DEV`、`nicstat` |
| **S** Saturation | 队列满、重传、overrun | `ip -s link` drop、`netstat -s` retrans、`ss` 队列 |
| **E** Errors | CRC、frame error、drop | `ethtool -S`、`ip -s link` |

→ [附录 A](./appendix-A-USE方法Linux.md)

### 工作负载与 TCP 分析

| 指标 | 意义 |
|------|------|
| **rx/tx bytes & pps** | 负载量级 |
| **并发连接数** | `ss -s` |
| **Retransmit rate** | 拥塞/丢包 — **`tcpretrans`** |
| **Out-of-order** | 路径多径/重排 |
| **Listen backlog 满** | 丢 SYN |
| **TIME_WAIT 数量** | 短连接扩展性 |

**HFT 红线：**

- 行情路径：**UDP 丢包率、pps、softirq CPU**
- 发单路径：**TCP RTT、重传、Send-Q 积压**

### 抓包（Packet Sniffing）

| 优点 | 代价 |
|------|------|
| 最全协议细节 | **CPU + 磁盘** 开销巨大 |

**Gregg：** 生产 **最后手段** — 优先 `ss`、`nstat`、BPF；抓包限时长、限 filter、mirror 口离线分析。

---

## 10.6 观测工具

### 传统统计

| 工具 | 用途 | 关键 |
|------|------|------|
| **`ss -tiepm`** | 套接字 **TCP 内部状态** | RTT、cwnd、retrans、mem、BBR 信息 |
| **`ip -s link`** | 接口吞吐、drop、overrun | `RX/TX errors` |
| **`nstat` / `netstat -s`** | SNMP 协议栈计数 | retrans、failed connects |
| **`sar -n DEV`** | 历史接口吞吐 | 容量/事后 |
| **`nicstat`** | 接口 %util 类指标 | 忙不忙 |
| **`ethtool -S`** | **驱动级** 统计 | NIC drop、no buffer |

```bash
ss -tiepm | head -50          # 看 RTT、重传、mss
ip -s link show eth0
nstat -az | grep -i retrans
ethtool -S eth0 | grep -i drop
```

### BPF / BCC

| 工具 | 作用 |
|------|------|
| **`tcplife`** | 每连接生命周期、吞吐 — **极实用** |
| **`tcptop`** | 按进程网络吞吐 |
| **`tcpretrans`** | 重传事件 + 栈 |
| **`tcpconnect` / `tcpaccept`** | 连接建立追踪 |
| **`bpftrace`** | 自定义丢包、内核栈 |

→ [Ch 15 BPF](./chapter-15-BPF技术.md) · [附录 C](./appendix-C-bpftrace单行命令.md) · [03-BPF](../03-BPF-Performance-Tools/)

### 抓包

| 工具 | 场景 |
|------|------|
| **`tcpdump`** | 服务器 CLI 过滤抓包 |
| **Wireshark** | 离线 decode、TCP 流分析 |

---

## 10.7–10.8 实验与调优

### 微基准与故障模拟

| 工具 | 用途 |
|------|------|
| **`iperf3`** | TCP/UDP 最大吞吐 |
| **`netperf`** | RPC 风格 RTT |
| **`tc netem`** | 注入 **delay/loss/reorder** — 混沌测试 |

```bash
iperf3 -c server -t 30 -P 4
tc qdisc add dev eth0 root netem delay 2ms loss 0.1%
```

**HFT：** 共置 baseline **iperf + 应用级 ping 订单通道**；netem 在 **测试环境** 验证策略 robustness。

### 系统级 sysctl（Netflix 示例思路）

| 参数 | 方向 | 说明 |
|------|------|------|
| **`net.core.netdev_max_backlog`** | ↑ | 入口队列 |
| **`net.core.somaxconn`** | ↑ | accept 队列 |
| **`net.ipv4.tcp_max_syn_backlog`** | ↑ | SYN 队列 |
| **`net.ipv4.tcp_rmem` / `tcp_wmem`** | ↑ | TCP 窗口上下限 |
| **`net.ipv4.tcp_congestion_control`** | `bbr` | 拥塞算法 |
| **`net.ipv4.tcp_tw_reuse`** | 1 | TIME_WAIT 重用（理解风险） |
| **`net.core.rmem_max` / `wmem_max`** | ↑ | socket buffer 上限 |

**HFT 注意：**

- 共置 **低延迟** 与云 **高吞吐** 参数集 **不同** — 勿盲抄 Netflix 全表。
- 与 **11-HFT ch05/ch06** 合并成 **单一 sysctl runbook**，变更可回滚。

→ [11-HFT ch06](../11-HFT-Low-Latency-Practice/chapter-06-低延迟网络.md)

### 套接字选项（应用层）

| 选项 | 效果 | HFT |
|------|------|-----|
| **`TCP_NODELAY`** | 禁 Nagle — **小包立即发** | 发单/低延迟 tick 常见 |
| **`TCP_CORK`** | 聚合小包 — 提吞吐 | 批量非紧急数据 |
| **`SO_REUSEPORT`** | 多进程 bind 同一端口 | 收包扩展 |
| **`SO_BUSY_POLL`** |  socket  busy poll | 降 latency、增 CPU |
| **非阻塞 + epoll** | 事件驱动 | Ch 5 · UNP |

→ [08-UNP](../08-UNP-Vol1/) · [01-CSAPP Ch11](../01-CSAPP-3rd/chapter-11-网络编程.md)

---

## 本章 Checklist

- [ ] 能分解 **DNS / 连接 / TTFB / RTT** — 不只说「网络慢」
- [ ] 会用 **`ss -tiepm`** 看 RTT、重传、队列
- [ ] 会用 **`ip -s link`**、**`nstat`** 看重传与 drop
- [ ] 跑过 **`tcplife`** 或 **`tcpretrans`** 至少一次
- [ ] 理解 **RSS/RPS/IRQ affinity** 与 softirq 的关系
- [ ] 知道何时查 **标准栈** vs **DPDK/XDP**（handbook 07–10 闭环）
- [ ] 生产抓包 **仅作最后手段**

---

## HFT 精读捷径（Ch 10 在路线中的位置）

```
Ch 5  应用线程状态、epoll、TCP_NODELAY
Ch 6  softirq CPU、绑核
Ch 7  socket buffer 与内存
Ch 10 网络（本章：栈、TCP、工具、sysctl）
  → 07 TCP/IP  协议语义
  → 08 UNP     socket API
  → 09 Rosen   内核实现
  → 10-DPDK    旁路落地
  → 03-BPF     XDP/tc 工具
  → 11-HFT     ch06/ch10 工程
```

**本章最小行动集：**

1. **`ss -s`** + **`ss -tiepm`** — 连接数、重传、典型 RTT。
2. **`ip -s link`** + **`ethtool -S`** — 有无 drop/overrun。
3. **`sudo tcpretrans-bpfcc 30`** — 看重传是否对齐延迟尖刺。
4. **行情/发单各一条延迟 span** — 对照 TTFB vs wire RTT。

**Gregg 本章金句（HFT 版）：**

> 网络是 **最常见的替罪羊** — 用 **分段延迟 + ss/BPF** 找真凶，别先买带宽。  
> **tcpdump 是最后手段**；`tcplife` 和 **`ss -tiepm`** 往往够用。

---

## 相关章节

- 上一章：[chapter-09-磁盘.md](./chapter-09-磁盘.md)
- 下一章：[chapter-11-云计算.md](./chapter-11-云计算.md)
- 协议：[07-TCP-IP-Illustrated-Vol1](../07-TCP-IP-Illustrated-Vol1/)
- Socket API：[08-UNP-Vol1](../08-UNP-Vol1/)
- 内核网络：[09-Linux-Kernel-Networking](../09-Linux-Kernel-Networking/)
- DPDK 旁路：[10-DPDK-Low-Latency-Network](../10-DPDK-Low-Latency-Network/)
- XDP：[03-BPF note-XDP](../03-BPF-Performance-Tools/note-XDP与tc-BPF.md)
- BPF：[chapter-15-BPF技术.md](./chapter-15-BPF技术.md)
- 跨模块对照：[CROSS-MODULE-GUIDE.md](../CROSS-MODULE-GUIDE.md)
- HFT 工程：[11-HFT ch06/ch10](../11-HFT-Low-Latency-Practice/)
- 全书目录：[OUTLINE.md](./OUTLINE.md)
