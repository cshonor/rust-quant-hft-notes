# Ch 14 Ftrace 跟踪 · Ftrace

> **Systems Performance 2nd** · Brendan Gregg · **选读**

> 本章定位：**Linux 内核内置的标准追踪框架** — 无需额外安装，通过 **tracefs** 配置，适合 **探索内核路径、调度、irq、函数调用图**。Ch 13 perf 可挂 tracepoint；Ch 15 BPF 是现代 HFT **主战场**；Ftrace 在 **内核 odd case、hwlat/SMI、无 BPF 老内核** 仍不可替代。  
> **HFT：** 日常用 **perf + bpftrace**；遇 **无法解释的停顿**（非 CPU/非 I/O/非锁）→ **hwlat**；深度查 **内核收发包/调度链** → `function_graph` / trace-cmd。

---

## 大白话 · 本章就五件事

> **Ftrace = 内核自带的「黑匣子」，写文件就能追。**

**① tracefs — 通过 `/sys/kernel/tracing` 读写配置追踪。**

- 内核自带，嵌入式/救援环境也能用 — 不依赖 BCC 包。

**② 函数追踪 + function_graph — 看内核谁调谁、耗多久。**

- 不只函数入口 — **入口+出口** 画 **带耗时的调用图**。

**③ 多事件源：tracepoint、kprobe、uprobe + filter/trigger。**

- **Hist trigger** — 内核里直接做直方图，聚合开销低。

**④ hwlat — 抓硬件/固件级停顿（含 SMI）。**

- P99 尖刺在 perf/BPF 都对不上时 — 怀疑 **BIOS/SMI**。

**⑤ 前端：trace-cmd、KernelShark、perf ftrace、Gregg perf-tools。**

- 老内核无 BPF → **perf-tools** 里 Ftrace 版 opensnoop/execsnoop 仍好用。

下面按原书 14.1–14.13 展开。

---

## 14.1–14.2 核心能力与 tracefs

### Ftrace 概述

| 演进 | 说明 |
|------|------|
| **起源** | **Function Tracer** — 追踪内核函数调用 |
| **现状** | 多追踪器框架：function、function_graph、tracepoint、hwlat… |
| **优势** | **内核自带**、无用户态依赖、资源受限环境可用 |

### tracefs 接口

挂载点（发行版二选一）：

```
/sys/kernel/debug/tracing   # debugfs（需 debug 挂载）
/sys/kernel/tracing         # 新式 tracefs 挂载
```

**交互方式：** 读写虚拟文件 — 配置 tracer、启停、读 buffer。

```bash
# 常见路径检查
ls /sys/kernel/tracing 2>/dev/null || ls /sys/kernel/debug/tracing

# 查看可用 tracer
cat /sys/kernel/tracing/available_tracers

# 当前 tracer
cat /sys/kernel/tracing/current_tracer
```

| 文件/目录 | 作用 |
|-----------|------|
| `current_tracer` | 选择追踪器（nop/function/function_graph…） |
| `tracing_on` | 0/1 开关 |
| `trace` | 一次性读 buffer |
| `trace_pipe` | **阻塞流式读**（类似 tail -f） |
| `set_ftrace_filter` | 限制追踪哪些函数 |
| `events/` | tracepoint 事件树 |
| `set_event` | 启用哪些 tracepoint |

**权限：** 通常需 **root** 或 `CAP_SYS_ADMIN` — 生产限时长、限 filter。

→ Ch 4 [Ftrace 在工具链中的位置](./chapter-04-观测工具.md)

---

## 14.3–14.4、14.8 函数追踪与 function_graph

### Function Tracing

追踪内核函数 **入口** — 极高体积，必须 **filter**。

```bash
TR=/sys/kernel/tracing
echo function > $TR/current_tracer
echo tcp_v4_rcv > $TR/set_ftrace_filter   # 示例：仅追踪该函数
echo 1 > $TR/tracing_on
# ... 产生负载 ...
echo 0 > $TR/tracing_on
cat $TR/trace | head -50
```

**风险：** 无 filter 的 function tracer **打爆 buffer、严重拖慢系统** — 仅短窗口 + 窄 filter。

### function_graph 追踪器

同时追踪 **入口 + 出口** → **调用图 + 每函数耗时**。

```bash
TR=/sys/kernel/tracing
echo function_graph > $TR/current_tracer
echo tcp_recvmsg > $TR/set_graph_function    # 图追踪起点
echo 1 > $TR/tracing_on
sleep 2
echo 0 > $TR/tracing_on
cat $TR/trace | head -80
```

**输出形态：**

```
tcp_recvmsg() {
  __skb_recv_datagram() {
    ...
  } /* 2.345 us */
} /* 5.678 us */
```

**HFT 用途：**

- 内核栈 **收包路径** 慢 — 从 `tcp_v4_rcv` / `udp_rcv` 往下追（对照 [09 Rosen](../09-Linux-Kernel-Networking/)）。
- 对比 **DPDK 旁路** 绕过了哪些函数（→ [10-DPDK](../10-DPDK-Low-Latency-Network/)）。

→ Ch 13 [perf 与 tracepoint 关系](./chapter-13-perf性能分析.md#追踪点事件tracepoint-events)

---

## 14.5–14.7、14.10 事件源、Filter 与 Hist Triggers

### 多数据源

| 源 | 说明 | 配置入口 |
|----|------|----------|
| **Tracepoints** | 内核静态观测点 | `events/.../enable` |
| **kprobes** | 内核动态函数插桩 | `events/kprobes/...` |
| **uprobes** | 用户态动态插桩 | `events/uprobes/...` |

```bash
# 启用 sched 切换 tracepoint
echo 1 > /sys/kernel/tracing/events/sched/sched_switch/enable
echo 1 > /sys/kernel/tracing/tracing_on
cat /sys/kernel/tracing/trace_pipe
```

### Filters 与 Triggers

| 机制 | 作用 |
|------|------|
| **Filter** | 只记录满足条件的事件（如 `pid == 1234`） |
| **Trigger** | 事件发生时执行动作（snapshot、stacktrace、**histogram**） |

**Hist Triggers（直方图触发器）：**

- 在 **内核内** 对事件字段做 **直方图聚合** — 不需把每条事件送到用户态。
- 支持：单键/多键、PID 过滤、**stacktrace**、**synthetic events**（合成事件链）。

**价值：** 高频率事件（如 sched_switch、net receive）— hist 比 raw trace **低开销**。

```bash
# 概念示例（语法随内核版本见 Documentation/trace/histogram.rst）
# echo 'hist:keys=pid:vals=latency' > .../trigger
```

**HFT：** 调度迁移 histogram — 看 hot thread 是否被 **频繁 cpu_migrations**（Ch 6/7）。

→ Ch 15 [BPF 可编程聚合](./chapter-15-BPF技术.md) — 新系统优先 BPF maps histogram

---

## 14.9 硬件延迟检测（hwlat）

### Hardware Latency Tracer

检测 **非 OS 可解释的长时间停顿** — 常见原因：

| 原因 | 说明 |
|------|------|
| **SMI** | 系统管理中断 — BIOS/固件 |
| **其他固件** | BMC、电源管理 |
| **硬件 bug** | 内存、PCIe |

```bash
TR=/sys/kernel/tracing
echo hwlat > $TR/current_tracer
echo 1 > $TR/tracing_on
sleep 30
echo 0 > $TR/tracing_on
cat $TR/trace
```

**何时用（HFT）：**

- **P99/P999 尖刺**；`perf`、`offcputime`、**biolatency** 都对不上
- CPU **非 idle 但 forward progress 停住**
- 裸机低延迟验收 — **hwlat baseline**

**对策：** 更新 BIOS、关 C-State/SMI 相关选项、换主板 — 与 [11-HFT ch05](../11-HFT-Low-Latency-Practice/chapter-05-操作系统内核极致调优.md) 联动。

---

## 14.11–14.13 前端工具

### trace-cmd

**Ftrace 的命令行前端** — 配置、录制、保存、回放。

```bash
# 录制 sched 事件 5 秒
trace-cmd record -e sched -p function_graph sleep 5
trace-cmd report | head

# 保存 trace.dat 供 KernelShark 打开
trace-cmd record -o trace.dat -e net -e sched sleep 10
```

| 优点 | 说明 |
|------|------|
| 简化 tracefs 手写 | 一条命令多 event |
| **record/report** | 可归档、可分享 |

### KernelShark

**trace-cmd 的 GUI** — 时间线、过滤、关联 CPU。

- 适合：**长时间 trace** 人工浏览 — 比 `cat trace` 可读。

### perf ftrace

`perf` 内置 Ftrace 前端 — 与 Ch 13 统一入口。

```bash
perf ftrace --tracer function_graph -- sleep 5
# 或 perf trace 走 tracepoint（见 Ch 13）
```

**分工：** 日常 **perf record/trace** 够用；专精 Ftrace 特性用 **trace-cmd**。

### perf-tools（Gregg 开源脚本集）

将 **Ftrace + 部分 perf** 封装为 **单用途工具**：

| 工具类 | 例子 |
|--------|------|
| 文件 | opensnoop、execsnoop |
| 网络 | tcpconnect、tcpretrans（老版 Ftrace 实现） |
| 磁盘 | 部分 biosnoop 前身 |

**何时仍需要：**

- **老内核** — 无 BCC/bpftrace/eBPF
- **最小环境** — 不能装 bpftrace 包
- **学习** — 看脚本如何写 tracefs

**现代 HFT 裸机：** 优先 **BCC/bpftrace**（Ch 15、03-BPF）；perf-tools 作 **fallback** 或读源码学 tracepoint。

→ https://github.com/brendangregg/perf-tools

---

## Ftrace vs perf vs BPF（选型）

| 需求 | 首选 |
|------|------|
| CPU 火焰图、PMC | **perf record**（Ch 13） |
| 内核函数 **调用图+耗时** | **Ftrace function_graph** |
| 高率事件 **内核直方图** | Ftrace hist / **BPF maps** |
| 硬件 **SMI 级停顿** | **Ftrace hwlat** |
| 生产 **通用追踪** | **bpftrace/BCC**（Ch 15） |
| 无 BPF 老系统 | **perf-tools / trace-cmd** |

```
Ch 4 工具地图
  perf ──────── 计数/采样/部分 trace
  Ftrace ────── 内核路径/graph/hwlat/hist
  BPF ───────── 可编程、生产主力（下一章）
```

---

## 本章 Checklist

- [ ] 知道 **tracefs** 路径与 `current_tracer` / `tracing_on`
- [ ] 理解 **function_graph** 与裸 **function** tracer 的区别
- [ ] 启用过至少一个 **tracepoint**（如 sched_switch）
- [ ] 知道 **hwlat** 用于 SMI/固件停顿排查
- [ ] 会用 **trace-cmd record** 保存 trace
- [ ] 明确 **HFT 日常 perf/BPF，Ftrace 补内核深度与 hwlat**

---

## HFT 精读捷径（Ch 14 在路线中的位置）

```
Ch 13  perf — 默认剖析器
Ch 14  Ftrace（本章：内核内置、function_graph、hwlat）
Ch 15  BPF — 生产追踪主力
  → 09 Rosen 内核网络路径
  → 10 网络 Ch10 softirq/NAPI
  → 03-BPF 专书
```

**按需精读：**

| 场景 | 读哪节 |
|------|--------|
| 内核收发包慢 | 14.3–14.4 function_graph + net tracepoint |
| 调度/jitter | 14.5 sched tracepoint + hist |
| 莫名尖刺 | **14.9 hwlat** |
| 老内核无 BPF | 14.11–14.13 perf-tools |

**本章最小行动集：**

1. 确认 **`/sys/kernel/tracing`** 可访问。
2. **`trace-cmd record -e sched sleep 2`** + `trace-cmd report | head`。
3. 低负载跑 **30s hwlat** — 记录是否有异常 latency 事件（baseline）。

**Gregg 本章金句（HFT 版）：**

> **Ftrace 是内核自带的显微镜** — 写 tracefs 就能追；**function_graph** 看内核链，**hwlat** 看固件鬼影。  
> 新系统 **BPF 优先**；Ftrace 在 **graph、hist、hwlat** 和 **无 BPF 环境** 仍不可替代。

---

## 相关章节

- 上一章：[chapter-13-perf性能分析.md](./chapter-13-perf性能分析.md)
- 下一章：[chapter-15-BPF技术.md](./chapter-15-BPF技术.md)
- 工具地图：[chapter-04-观测工具.md](./chapter-04-观测工具.md)
- 内核网络：[09-Linux-Kernel-Networking](../09-Linux-Kernel-Networking/)
- BPF 专书：[03-BPF-Performance-Tools](../03-BPF-Performance-Tools/)
- HFT 调优：[11-HFT ch05](../11-HFT-Low-Latency-Practice/chapter-05-操作系统内核极致调优.md)
- 全书目录：[OUTLINE.md](./OUTLINE.md)
