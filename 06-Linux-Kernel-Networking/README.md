# Linux Kernel Networking — Rami Rosen

**文件夹 06 · 原书目第 4 册** · [返回总清单](../READING-LIST.md#4-linux-kernel-networking--rami-rosen)

## 本书 HFT 读法

| 标签 | 含义 |
|------|------|
| **必读** | 本文件夹有笔记 · 精读，HFT 主线建议认真读 |
| **选读** | 本文件夹有笔记 · 选读，有余力再读 |
| **跳过** | 本文件夹无笔记，当前 HFT 目标下默认不读 |

> 有 `.md` 的章节 = 建议做笔记；没建文件的章节 = 默认跳过（有特殊需求再读）。

## 必读（精读）

| 主题 | 笔记文件 |
|------|----------|
| Socket 层 / sk_buff 路径 | [chapter-01-Socket与sk_buff路径.md](./chapter-01-Socket与sk_buff路径.md) |
| UDP 实现 | [chapter-03-UDP实现.md](./chapter-03-UDP实现.md) |
| NAPI / softirq / Net RX | [chapter-05-NAPI与收包路径.md](./chapter-05-NAPI与收包路径.md) |
| Multicast（IGMP/组播） | [chapter-06-组播IGMP.md](./chapter-06-组播IGMP.md) |
| RSS / RPS / XPS | [chapter-07-RSS与多队列.md](./chapter-07-RSS与多队列.md) |

## 选读

| 主题 | 笔记文件 | 升级条件 |
|------|----------|----------|
| TCP 栈实现 | [chapter-02-TCP协议栈.md](./chapter-02-TCP协议栈.md) | 订单通道走 TCP → 升为必读 |
| IP 层 / Routing | [chapter-04-IP层与路由.md](./chapter-04-IP层与路由.md) | 同机房/托管网络部署时细读 |

## 跳过（无笔记文件）

- Netfilter / iptables 深读 — 生产 HFT 通常旁路或最小化
- Wireless / Bluetooth

## HFT 产出

从网卡 DMA → NAPI → 用户态 socket 的完整内核路径；与 UNP、DPDK 文档对接。
