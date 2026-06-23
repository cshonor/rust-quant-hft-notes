## 1.6–1.8 核心指标与观测 / 实验工具

### 延迟 Latency — HFT 订单链路怎么读数

- **最基本、最重要**的性能指标 — 可量化问题、估算理论改进空间（Amdahl / 关键路径）
- **HFT 核心：抓长尾、拆链路** — 别在 **平均延迟** 上死磕；实盘怕的是 **偶尔掉链子的 0.1%**

#### 三类延迟指标 — HFT 怎么分类读

| 类 | 指标 | 含义 | 典型用途 |
|----|------|------|----------|
| **① 平均类** | **Mean 平均** | 所有请求耗时的算术平均 | **压测基线**：优化后先看均值是否压进目标（如 10μs 以内） |
| **② 分位类** | **P50 / P99 / P999** | P50=中位数；P99/P999= **99%/99.9% 请求的上限** | 长尾：**最慢 1%、0.1%** — 行情峰值是否掉链子 |
| **③ 极值类** | **Max 最大延迟** | **单次**最坏情况 | HFT 有时 **比 P999 还敏感** — 只出现 **一次 >1ms** 也可能实盘大亏 |

```
平均 10μs  +  P999 150μs  +  Max 1.2ms（一天只一次）
  → 平时、P999 统计上都可能「还行」
  → 但那一次 Max 撞上跳空 → 整笔滑点吃掉一周 alpha
```

**HFT 优化优先级（和普通业务相反）：**

```
1. 先卡死 Max 上限          ← 绝不允许的单次灾难
2. 再压 P999 / P99 抖动     ← tail 分布
3. 最后才抠平均延迟         ← 均值再低，一次 tail 可全白搭
```

| 阶段 | 看什么 | 通过标准（举例） |
|------|--------|------------------|
| 压测回归 | Mean ↓ | 方向对了 |
| 实盘 SLO | P99 / P999 | 绝大多数 tick 稳 |
| 红线 | **Max** | 任何一次不得超硬上限 |

**HFT vs 普通业务：**

| | 普通业务 | HFT |
|---|----------|-----|
| 优化顺序 | 平均 → P95 常够 | **Max → P999 → Mean** |
| 长尾 | 可接受偶发慢 | **一次 Max 撞上峰值 = 盈亏** |

→ 测量：[HFT ch10 延迟测量](../../../11-HFT-Low-Latency-Practice/chapter-10-延迟测量与基准压测/) · [Ch 12 基准测试](../../chapter-12-benchmarking/)

#### 观测工具 ↔ 三类指标 — Metrics / Tracking / Profiling

| 工具类 | 典型代表 | 主要盯哪类指标 | 干什么 |
|--------|----------|----------------|--------|
| **Metrics 指标** | histogram、Prometheus、应用内分位统计 | **Mean + P50/P99/P999 基线** | 生产/压测 **持续盯分位曲线**；SLO 告警 |
| **Tracking 追踪** | ftrace、eBPF/bpftrace、perf trace | **Max / 单次 tail** | **偶尔冒头**的那一笔 — 逐步拆 RX→栈→策略→TX |
| **Profiling 剖析** | perf、火焰图 | tail **根因嫌疑** | 定位 **那次** Max 对应的热路径函数 / 锁 / syscall |

**计数器**（`mpstat`、`ethtool`）补 **resource 基线** — 与 Metrics 一起看「路况是否正常」，不替代分位与 Max。

**固定工作流：**

```
Metrics   →  P999 曲线升高了？Max 告警？
Tracking  →  抓住那一次 spike，分段 timestamp
Profiling →  同期 perf 火焰图 / 锁分析，找根因
```

**单笔全链路拆段（Tracking）：**

```
网卡收包 (RX) → 内核协议栈 / bypass → 策略计算 → 网卡发包 (TX)
```

| spike 类型 | Tracking 可能看到 | 落地 |
|------------|-------------------|------|
| Max +1ms | 线程 **换出 ~100μs+** | isolcpus、绑核 |
| 偶发解析尖刺 | **page fault** | mlock、预 fault |
| 发单尖刺 | **锁 / syscall** | 内存池、长连接 |

**别把工具用反：**

| 错 | 对 |
|----|-----|
| 只优化 Mean，不盯 Max | **先 Max 红线，再 tail，最后 Mean** |
| 只用 Metrics 平均值告警 | 必须 **histogram + Max 捕获** |
| Max 出现后才凭感觉改代码 | **Tracking 抓样本 → Profiling 定根因** |

### 观测 Observability — 四层递进：扫盲 → 趋势 → 热路径 → 拆单笔

Gregg 四类工具 = **从粗粒度统计到全链路追踪** 的排障阶梯；HFT 一般 **按顺序走，别跳层**。

```
计数器 Counters  →  指标 Metrics  →  剖析 Profiling  →  追踪 Tracing
   「有没有异常」     「什么时候开始高」   「哪段代码宽」      「这一笔逐步花在哪」
```

| 层 | 是什么 | 典型例子 | 回答什么 |
|----|--------|----------|----------|
| **① 计数器** | 最基础 **次数/累计** 统计 | 网卡收包数、`cache-misses`、softirq 次数、`ethtool -S` drop | 系统 **有没有异常波动**？resource 路况正常吗？ |
| **② 指标 Metrics** | **带时间维度** 的计数器/聚合 | 每秒收包延迟 histogram、P99 曲线、Prometheus 时序 | **什么时候开始高**？趋势还是尖刺？SLO 告警 |
| **③ 剖析 Profiling** | 一段时间内 **函数调用占比** 采样 | `perf record -g`、**火焰图** | **热路径哪段最宽**？平均/采样意义上的瓶颈 |
| **④ 追踪 Tracing** | **单个请求** 全链路耗时拆解 | eBPF、ftrace、分段 timestamp | **这一笔** P999/Max：RX→栈→策略→TX 各多少 μs？ |

**HFT 排障顺序（固定套路）：**

```
1. 计数器 + 指标   →  确认「延迟确实高了 / P999 曲线抬升 / Max 告警」
2. 剖析           →  火焰图定位热路径、嫌疑函数
3. 追踪           →  把 **那一次** 长尾逐步拆透 → 可落地优化点
```

**和三类延迟指标的对应：**

| 延迟指标 | 主要靠哪几层 |
|----------|--------------|
| Mean / 压测基线 | 计数器 + Metrics |
| P99 / P999 | Metrics（histogram）+ Profiling（嫌疑） |
| **Max** | Metrics 捕获 + **Tracing 必做** |

| 类型 | 作用 | 后续章节 |
|------|------|----------|
| **计数器 Counters** | 累计事件（中断次数、包数） | Ch 4、Ch 6–10 |
| **指标 Metrics** | 时间序列、分位聚合 | 生产监控 |
| **剖析 Profiling** | 谁在耗 CPU — **火焰图** | Ch 13 perf、Ch 4 |
| **追踪 Tracing** | 单次时间线、因果 | Ch 14 Ftrace、Ch 15 BPF |

**HFT 命令速查：**

```bash
# ① 计数器 — 扫盲
mpstat -P ALL 1          ethtool -S eth0          perf stat -e cache-misses

# ② 指标 — 应用内 histogram / P99 曲线（或 Prometheus）

# ③ 剖析 — 热路径
perf record -g -p <pid> -- sleep 30 && perf report

# ④ 追踪 — 单笔 tail（示例方向，具体脚本见 Ch15）
# bpftrace / ftrace：订单 ID 关联 RX→decode→send 各段 Δt
```

→ [03-BPF Performance Tools](../../../03-BPF-Performance-Tools/) · [Ch 4 工具选型](../../chapter-04-observability-tools/) · [Ch 13 perf](../../chapter-13-perf/) · [Ch 14 ftrace](../../chapter-14-ftrace/) · 双视角排障 [1.4](./section-1.4-1.5-分析视角与性能挑战.md)

### 实验 Experimentation（主动施加负载）

| 类型 | 测什么 | 例子 |
|------|--------|------|
| **宏观基准 Macro-benchmark** | 真实场景端到端 | 全链路压测、回放行情 |
| **微观基准 Micro-benchmark** | 单组件 | 内存带宽、syscall 开销、单函数 |

**HFT：** 微观基准易脱离真实（见 Ch 12）；宏观需**生产级 workload**（真实报文率、订单形状）。

### 观测 vs 实验

| | 观测 | 实验 |
|---|------|------|
| 目的 | 理解**正在运行**的系统 | **主动制造**负载做对比 |
| 风险 | 生产开销需控制 | 合成负载可能不代表真实 |
| 工具倾向 | `perf`、bpftrace、`sar` | `fio`、自定义压测、testpmd |

---


---

← [本章导读](../README.md)
