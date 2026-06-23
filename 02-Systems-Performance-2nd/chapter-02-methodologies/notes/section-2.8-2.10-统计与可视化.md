## 2.8–2.10 统计与可视化

> **HFT 性能统计的铁律：** 盯 **分位值（P99/P999）**、**标准差**、**异常值** — **别被平均数骗了**。  
> ← [2.5 埋点 / histogram](./section-2.5-性能分析方法论.md) · [2.7.2 容量 SLO](./section-2.7.2-容量规划三步法.md) · [Ch1.6 延迟读法](../chapter-01-intro/notes/section-1.6-延迟指标与读法.md)

---

### 三大统计陷阱（HFT 最致命）

Gregg 2.8–2.10 的核心警告：延迟分布 **很少是正态** — 用 **mean** 做 SLA 在 HFT 里等于 **自我安慰**。

---

### 实盘：为什么 tail 不是「小数点」— 交易所硬规则 + 抢单经济学

统计陷阱不是学术题 — **国内期货**等市场有 **超时撤单/丢弃** 硬规则（示意：**会员网关 → 撮合引擎** 全链路耗时有上限，常见量级 **500 ms** 级，以各交易所现行规则为准）。同时 **私募到交易所的专线** 本身占 **几十 μs～1 ms** — 这是 **减不掉的固定延迟**。

**端到端要留 budget：**

```
总延迟 ≈ 专线(几十μs~1ms) + 你的网关/引擎 + 交易所侧处理
         └─ 固定 ─┘   └── P99/P999 盯这里 ──┘
```

| 段 | 量级 | 说明 |
|----|------|------|
| 专线 RTT | **~50 μs–1 ms** | 共置/低延迟线路仍非零 |
| 引擎 **mean** | 50 μs | 汇报「很好」 |
| 引擎 **P999** | **2 ms** | mean **完全看不见** 的 1% |
| 交易所硬限 | **~500 ms**（品类/规则各异） | 超限 → **订单直接丢弃** |

**两点要分开看：**

1. **硬上限（500 ms 级）** — 正常 HFT 远不会贴线跑；但若 **排队雪崩、GC ms 级、重传** 等 tail **叠加**，极端窗口仍可能触达 — tail 是 **安全余量** 的敌人。
2. **抢单竞争（μs～ms 级）** — 这才是 **日常致命处**：引擎 P999 **2 ms**，加上专线 **1 ms**，你比对手 **慢 3 ms** — 往往 **已错过最优档**，即使 **订单没被交易所拒**，**滑点也把利润吃光**。

**策略经济学（量级感，因品种/频率而异）：**

| 说法 | 含义 |
|------|------|
| **每 1 ms 延迟** | 高频场景下单日收益 **可掉 10% 以上**（edge 薄、竞争在 μs 级） |
| **1% 长尾（P99/P999）** | 不是「偶发噪声」— **足以让策略从盈利变亏损** |
| **mean 50 μs + P99 2 ms** | 99% 单在赚钱节奏，**1% 坏单拖垮全天 P&L** |

**HFT 策略靠「抢单」** — 慢 **2 ms** = 价位被别人拿走；统计上必须 **按分位验收**，不能凭 mean 签收上线。

→ 与 [2.7.2 SLO 定目标](./section-2.7.2-容量规划三步法.md)（P99<10 μs）· [2.6 排队雪崩](./section-2.6.2-M-M-1-拐点与预警线.md) 衔接

---
#### 陷阱 ① · 平均延迟骗局（Mean 掩盖 tail 风险）

**现象：** 报单 **平均延迟 50 μs**，汇报「性能很好」— 但 **1% 的请求跑到 2 ms**。

| 指标 | 读数 | 实盘含义 |
|------|------|----------|
| **Mean** | 50 μs | 「看起来正常」 |
| **P99** | 2 ms | **40× 于均值** — 每 100 单约 1 单踩 tail |
| **后果** | — | **拒单 / 滑点 / 抢单失败** — 1% 坏单可拖垮全天 P&L（见上节） |

**为什么 mean 骗人：** 99% 快单把 1% 慢单「平均掉」了 — **风险全在 tail**，mean **完全看不见**。

```
延迟分布（示意）
  │ ████████████  99%  < 60 μs
  │               ▌ 1%  → 2 ms   ← mean 仍≈50μs，SLA 已炸
  └──────────────────────────
```

**HFT 做法：** SLO 写 **P99 / P999 / Max**，不写 mean；Grafana 面板 **mean 与 P99 同屏**，mean 绿、P99 红 = 立即查 tail。

→ [2.1 术语：P99 不是 mean](./section-2.1-HFT术语与团队对齐.md)

---

#### 陷阱 ② · 典型双峰问题（Bimodal · 两个「世界」）

**现象：** 延迟分布有 **两个峰** — 平时一簇、异常时另一簇；**mean 落在两峰中间**，不代表任何真实体验。

| HFT 场景 | 快峰 | 慢峰 | mean 的谎言 |
|----------|------|------|-------------|
| **Cache** | L1/L2 命中 ~100 ns | miss → μs | mean「还行」，miss 决定 tail |
| **带 GC 的语言** | 稳定 ~几十 μs | **GC 停顿 → ms 级** | mean 稳定，**GC 尖刺致命** |
| **快慢路径报单** | 快路径 5 μs | 慢查风控 500 μs | mean ~50 μs，两类单混在一起 |

**带 GC 引擎：** 平时延迟漂亮，**GC 触发时整条链路飙高** — 只看均值会漏掉 **最致命的波动**；开盘 burst 若撞上 GC，等于主动送 reject。

**HFT 做法：**

- **histogram 看几峰** — 两峰就要 **拆开统计**（快路径 P99 vs 慢路径 P99）
- **热力图 / 时间序列** — 尖刺是否 **周期性**（GC 周期、定时任务）
- 热路径：**C++/Rust、预分配、对象池** — 从架构上 **消第二峰**

---

#### 陷阱 ③ · 误读异常值（把 P999 当「偶发噪声」）

**现象：** P999 = 5 ms，团队说「偶发、可忽略」— **HFT 里 tail 不是噪声，是 P&L**。

| 错误心态 | 正确读法 |
|----------|----------|
| 「999 才 0.1%，不算数」 | 万单/s 下仍是 **大量坏单**；**盈利策略可因此变亏** |
| 「擦除 outlier 再算 mean」 | **outlier 往往是真 bug**（锁、GC、IRQ、NUMA） |
| 「只有 mean 达标就行」 | **抢单看 tail** — 慢 2 ms 错过最优价，滑点吃光 edge |

**长尾决定：**

- 能否 **在时限内成交**
- **reject / timeout** 率是否击穿风控
- 做市 **报价是否被 pick off**

**HFT 做法：** **P999、Max 进告警**；每个 outlier **可追溯**（[2.5 trace / histogram](./section-2.5-性能分析方法论.md)）；压测报告 **必须带分位数曲线**，不单报 mean。

---

### 该看什么 · 统计指标优先级

| 优先级 | 指标 | 用途 |
|--------|------|------|
| **P0** | **P99、P999、Max** | SLA、告警、容量 sign-off |
| **P1** | **标准差 σ、IQR** | 抖动大不大；双峰时 σ 虚高，配合 histogram |
| **P2** | **Mean** | 仅作 **容量 / 排队论** 粗估（与 [2.6](./section-2.6.1-排队论概览与Kendall记号.md) 模型对齐），**不作 SLA** |
| **P3** | **Outlier 列表** | 单笔 trace 定位根因 |

**自检一句：** 若面板只有 mean — **等于没做 HFT 性能统计**。

---

### 五种图 · 场景怎么用 + C++/Rust 怎么出图

> **路径一致：** 先 **埋点 / 采样**（[2.5](./section-2.5-性能分析方法论.md)）→ **线上 Grafana 盯趋势** → **线下 perf 火焰图 / FlameScope 抓 tail 根因**。  
> C++ 与 Rust **工具链大体相同**；差别主要在 **计时 API** 与 Rust 的 **`cargo flamegraph`** 一键链路。

| 图 | 一眼回答什么 | 典型场景 |
|----|--------------|----------|
| **折线图** | 指标 **随时间** 怎么变？有没有尖峰？ | 盯盘、压测、告警 |
| **散点图** | **负载 vs 延迟** 啥关系？拐点在哪？ | 定限流、找 knee |
| **热力图** | 延迟在 **什么时间 / 什么区间** 聚集？ | 周期抖动、长尾规律 |
| **火焰图** | **CPU 时间** 烧在哪个函数？ | 热点优化 |
| **FlameScope** | **哪段时间** 异常？正常 vs 异常栈差在哪？ | 偶发 tail、难复现 |

---

#### ① 折线图（Line Chart）

**平时怎么用：**

- 盘前 / 开盘 **前 30 分钟**：报单 **P99、mean**、**CPU 使用率** 随时间曲线 — **一眼看尖峰**（排队、burst、GC 前兆）
- 压测 **阶梯加压**：每个档位的延迟是否稳定
- 与 [2.6 预警线](./section-2.6.2-M-M-1-拐点与预警线.md) 对齐：ρ 曲线是否逼近 **60% 告警**

**HFT 场景：** 日常盯盘、On-call、容量复盘 — **时间序列是第一面板**。

**工具链（C++ / Rust 相同套路）：**

```
代码埋点 → Prometheus exporter → Grafana 折线面板
```

| 步骤 | C++ | Rust |
|------|-----|------|
| 计时 | `std::chrono::steady_clock` / `high_resolution_clock` | `std::time::Instant` |
| 导出 | prometheus-cpp / 自建 counter+histogram HTTP | `metrics` / `prometheus` crate |
| 展示 | **Grafana** — Query：`histogram_quantile(0.99, ...)`、`rate(...)` | 同左 |

---

#### ② 散点图（Scatter Plot）

**平时怎么用：**

- 横轴 **每秒报单量 λ**，纵轴 **对应 P99 / mean 延迟** — 每个点是一档压测或一分钟聚合
- **直观看到拐点**：流量到多少时延迟 **陡增** → 直接定 [限流阈值 / ρ 预警](./section-2.6.2-M-M-1-拐点与预警线.md)
- 验证排队论：是否在 **70% / 80%** 利用率附近 knee

**HFT 场景：** [2.7.2 压测验证](./section-2.7.2-容量规划三步法.md)、Ch12 阶梯加压报告 — **比单看折线更贴「容量」**。

**工具链：**

| 方式 | 做法 |
|------|------|
| **Grafana** | XY Chart / scatter：X=`orders_per_sec`，Y=`p99_latency_us`（Prometheus 或 CSV 数据源） |
| **Python** | 压测日志 → `matplotlib.pyplot.scatter` / **Seaborn** `scatterplot` |
| 埋点 | 同折线 — 每窗口聚合 **(λ, P99)** 一对写入 TSDB 或 CSV |

C++/Rust 侧 **无专用「散点命令」** — 关键是 **按窗口输出 (rate, latency)**，可视化在 Grafana / Python。

---

#### ③ 热力图（Heat Map）

**平时怎么用：**

- 横轴 **时间**（分钟 / 秒 offset），纵轴 **延迟分桶** 或 **请求序号**，颜色 = **密度 / 计数**
- 抓 **长尾规律**：是否 **每分钟固定一条竖带**（定时任务）、**开盘 9:30 一块红区**（burst）
- 怀疑 **网卡中断、内核调度、NUMA 迁移** 导致 **周期性掉延迟** — 热力图比折线更容易 **看聚集**

**HFT 场景：** 排查「**每天固定时段 P99 飙**」、GC/IRQ 周期、双峰里的 **慢峰何时出现**。

**工具链：**

| 方式 | C++ / Rust 通用命令 / 库 |
|------|--------------------------|
| **perf 热力** | `perf record -a -F 99 sleep 60` → **`perf heatmap`**（需 Brendan Gregg 系工具链 / 新版本 perf 插件，环境支持时） |
| **埋点 → Python** | 导出 `(timestamp, latency_us)` CSV → **Seaborn** `heatmap` / `hist2d` / `kdeplot` |
| **Grafana** | **Heatmap** 面板 — bucket 延迟 histogram over time（Prometheus `*_bucket`） |

```python
# 示意：一天延迟 (time_of_day_min, latency_bucket) → 颜色=count
import seaborn as sns
import pandas as pd
# df: columns [minute, latency_us]
sns.histplot(data=df, x="minute", y="latency_us", bins=50, cbar=True)
```

---

#### ④ 火焰图（Flame Graph）

**平时怎么用：**

- **谁吃 CPU** — 宽条 = 热点函数；报单引擎里 **订单簿排序、序列化、锁** 是否过宽
- **线下压测 / 短窗口 perf** — 解释「P99 高的时候 CPU 在干嘛」
- 与折线/热力图 **联动**：先知道 **何时** 慢，火焰图答 **哪个函数**

**HFT 场景：** 策略热点、锁争用、意外 `malloc` — [Ch 13 perf](../../chapter-13-perf/)。

**工具链：**

**C++（Linux perf + FlameGraph）：**

```bash
perf record -F 99 -p $(pidof gateway) -g -- sleep 30
perf script | stackcollapse-perf.pl | flamegraph.pl > flame.svg
# 浏览器打开 flame.svg
```

**Rust：**

```bash
cargo install flamegraph
cargo flamegraph --bin your_gateway -- -your args
# 生成 flamegraph.svg；底层仍是 perf + 栈折叠
```

| 注意 | 说明 |
|------|------|
| 编译 | `-g` 或 `-fno-omit-frame-pointer`；Rust `--release` 带 debuginfo |
| 实盘 | **短窗口、低频率** 采样 — 别长期 `-F 999` 压生产 |

---

#### ⑤ FlameScope

**平时怎么用：**

- 在 **火焰图之上加时间轴**：**长周期** 采样（分钟～小时）叠成 **可拖拽** 的「子火焰图」
- **偶发 tail、压测难复现**：在 FlameScope 里 **框选 P99 飙高的那 30 秒** → 看该窗 **调用栈 vs 正常窗** 差在哪
- 对付 [2.8 陷阱③](./section-2.8-2.10-统计与可视化.md#陷阱-③--误读异常值把-p999-当偶发噪声)：**outlier 不是噪声** — 要 **时间定位 + 栈对比**

**HFT 场景：** 「一天只坏几次的 2 ms」— Grafana 看到尖刺 → FlameScope 精确定位 **那几秒在跑什么**。

**工具链（C++/Rust 共用 perf 数据）：**

```bash
# 1. 采长窗口（注意磁盘，perf.data 会变大）
perf record -F 49 -p $(pidof gateway) -g -- sleep 300

# 2. 克隆 FlameScope（一次性）
git clone https://github.com/Netflix/flamescope.git

# 3. 生成 perf folded / 按 FlameScope 文档导入 perf.data
#    浏览器打开 FlameScope UI → 拖拽时间条 → 对比 sub-flamegraph
```

→ [FlameScope 项目](https://github.com/Netflix/flamescope) · Gregg 系 **HeatMap + 火焰图** 组合

---

### 五种图 · 选型速查

| 你想问… | 用哪张图 | 线上 / 线下 |
|---------|----------|-------------|
| 刚才 P99 是不是尖了一下？ | **折线** | Grafana |
| 报单加到多少该限流？ | **散点** | 压测 + Grafana / Python |
| 是不是每分钟/GC/IRQ 规律抖？ | **热力** | Grafana heatmap / Seaborn / perf heatmap |
| 哪个函数最吃 CPU？ | **火焰** | `perf` + FlameGraph / `cargo flamegraph` |
| 偶发 2 ms 那几秒栈里是谁？ | **FlameScope** | 长 `perf record` + 网页框选 |

**线上组合：** Grafana **折线（P99+mean）+ Heatmap**  
**线下组合：** **perf 火焰图** 定热点 → **FlameScope** 抓偶发 tail

→ [Ch 13 perf](../../chapter-13-perf/) · [Ch 15 BPF](../../chapter-15-bpf/) · [Ch1.7 观测四层](../chapter-01-intro/notes/section-1.7-观测工具四层递进.md)

---

### 与前面章节的衔接

| 章节 | 关系 |
|------|------|
| [2.5 埋点](./section-2.5-性能分析方法论.md) | histogram 产出 P99/P999 — 统计陷阱的 **数据源** |
| [2.6 排队论](./section-2.6.1-排队论概览与Kendall记号.md) | 模型给 **mean W** — 须用分位数 **校准 tail** |
| [2.7.2 容量 SLO](./section-2.7.2-容量规划三步法.md) | 定目标写 **P99<10 μs**，不写 mean |
| [2.4 Workload](./section-2.4-两种分析视角.md) | 业务视角 **Duration 看分位** |

---

### 检查单

- [ ] SLA / 容量目标用 **P99、P999**，不用 mean 签收
- [ ] Grafana：**P99 与 mean 同屏**；P99 告警独立阈值
- [ ] histogram 看过 **是否双峰**（GC、cache、快慢路径）
- [ ] **不随意删 outlier** — 每笔 P999 可 trace
- [ ] 压测报告含 **分位曲线 + 热力图**，不单报平均延迟

---

← [2.7.2 容量规划](./section-2.7.2-容量规划三步法.md) · [本章导读](../README.md)
