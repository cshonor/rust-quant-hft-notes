# Ch 17 套利者 · Arbitrageurs

> **Trading and Exchanges** · Larry Harris · **精读** · Part IV · **Ch 10 知情四类之分册**

本章探讨 **套利者 (Arbitrageurs)** 的交易策略、面临的 **各类风险**，以及套利在 **市场微观结构** 中的经济学角色。套利者不仅是 **信息交易者**，更是跨市场流动性的 **「搬运工」**。

> **HFT 核心章：** **ETF/期货 basis、pairs/stat arb、multi-leg execution、LTCM 教训** 的理论根；与 [Ch 10](./chapter-10-知情交易者与市场效率.md) · [Ch 16 价值（绝对 V）](./chapter-16-价值交易者.md) · [Ch 13 做市（时间维度）](./chapter-13-做市商.md) 对照。

---

## 1. 基本概念

### 1.1 定义

**套利者**：根据 **相对价值 (Relative values)** 信息交易的投机者。

```
买入相对便宜  +  卖出相对昂贵
        ↓
基差向正常关系回归（收敛）→ 获利
```

| vs 价值交易者 | Value 估 **绝对 V**；Arb 估 **相对关系** |
|---------------|----------------------------------------|

→ [Ch 10 §2.1](./chapter-10-知情交易者与市场效率.md) · [Ch 16](./chapter-16-价值交易者.md)

### 1.2 对冲投资组合 (Hedge Portfolios)

通过 **多头 + 空头** 尽量消除 **市场层面共同风险** — 组合的各 **腿 (Legs)**。

| HFT 视角 |
|----------|
| **Basket / spread / basis trade** — 多腿同步是 **execution 核心** |
| **Beta-neutral、sector-neutral** 是 **hedge portfolio** 的现代说法 |

### 1.3 基差 (Basis) 与套利价差 (Arbitrage Spread)

| 术语 | 定义 |
|------|------|
| **基差 (Basis)** | 对冲组合中 **不同工具之间的价差** |
| **套利价差** | 基差与其 **公平价值 (Fair value)** 之间的差额 |
| **入场条件** | 仅当套利价差 **足够大** — 超出 **套利边界 (Arbitrage band)** |

```
Fair value of basis  =  运输/融资/股息/便利收益等
Arbitrage spread     =  Actual basis − Fair value
Trade if |spread| > transaction costs + risk premium
```

| HFT 视角 |
|----------|
| **Fair value model**（期货–现货、ETF–NAV、ADR–本地）驱动 **signal** |
| **Band** 含 **fees + half-spread × legs + slippage buffer** |

---

## 2. 套利的两大类型

按 **基差风险性质** 划分：

### 2.1 纯粹套利 (Pure Arbitrages)

对冲组合价值 **均值回归 (Mean-reverting)** — 长期风险 **极低**；有 **明确机制** 保证收敛。

| 子类 | 机制 |
|------|------|
| **运输套利 (Shipping)** | 跨市场买卖 **同一实物**；价差 > 运输成本 → 运货或等收敛 |
| | **实际承运人** vs **虚拟承运人**（不运货，等价格收敛） |
| **交割套利 (Delivery)** | **期货–现货** 价差；**到期交割** 强制收敛 |
| **转换套利 (Conversion)** | 相同风险、不同形式 — **期权动态对冲**、大豆→豆油+豆粕 **压榨套利** |
| | 类似金融工程 **「制造」(Manufacturing)** |

| HFT 视角 |
|----------|
| **Cash-and-carry、reverse basis** — 交割套利电子化 |
| **Index arb、ETF creation** — conversion 变体 |
| **Box spread、put-call parity** — 期权 conversion |

### 2.2 投机性套利 / 风险套利 (Speculative / Risk Arbitrages)

存在 **工具特有估值因素** → 组合价值 **非平稳 (Nonstationary)**，但 **短期强均值回归** — **风险较高**。

| 子类 | 说明 |
|------|------|
| **价差交易 (Spreads)** | 除一特征外 **几乎相同** — **日历价差 (Calendar)**、收益率曲线 |
| **配对交易 (Pairs)** | 高相关工具（如 Ford / GM）**相对价错位** — 买便宜卖贵 |
| **统计套利 (Statistical arbitrage)** | **多因子模型** 识别多工具定价不一致 → **优化组合** |
| **风险套利 (Risk arb)** | 常指 **并购套利 (Merger/Takeover)** — 宣布后 **买目标、空收购方** |
| | 风险：**交易失败 / 条款变更** |

| HFT 视角 |
|----------|
| **Stat arb / pairs** = HFT **主策略类之一** — 本章 **risk arb 框架** 直接适用 |
| **Merger arb** — event-driven，非典型 HFT 但 **deal break gap** 同类 |
| **Nonstationary** → **model drift**、**regime change** 须监控 |

---

## 3. 四大核心风险

套利 **绝非无风险提款机**。

### 3.1 执行风险 (Implementation Risk)

| 问题 | 交易成本 **高于预期** |
|------|----------------------|
| **限价单不确定性** | **「冰块上的探险者」** — 一腿成交，另一腿 **价格跑掉** → **巨大敞口** |

| HFT 视角 |
|----------|
| **Leg risk** — 多 venue 同步、**IOC/FOK**、**synthetic spread order** |
| **Partial fill** 管理 — 自动 **hedge orphan leg** |
| **Latency skew** 跨市场 — 一腿快一腿慢 |

### 3.2 基差风险与规模 (Basis Risk and Scale)

| 问题 | 基差 **向不利方向扩大** |
|------|-------------------------|
| **纪律** | **忌满额杠杆** — 须 **持有能力 (Staying power)** |
| | 基差阶段性扩大时 **不被迫平仓** |
| **教训** | **LTCM** — 杠杆过大 + 基差扩大 → **爆仓** |

| HFT 视角 |
|----------|
| **Risk limits on gross/net exposure** per spread |
| **Drawdown tolerance** vs **margin call** — 与 prime broker **credit line** |
| **Crowded trade** — 基差扩大因 **多人同 arb** |

### 3.3 模型 / 分析风险 (Model / Analytic Risk)

| 错误 | 误解 **真实关系** |
|------|-------------------|
| | 把 **非套利** 当套利 |
| | **错误对冲比率 (Hedge ratio)** |

| HFT 视角 |
|----------|
| **Cointegration break**、**structural change**（并购、退市） |
| **Beta 估计误差** — pairs 关系 **非恒定** |

### 3.4 持有成本风险 (Carrying Cost Risk)

| 来源 | 说明 |
|------|------|
| **追加保证金** | 空头腿标的 **暴涨** |
| **收敛缓慢** | 时间 **耗损 carry** |
| **强制平仓** | **Forced buy-in**、**逼空 (Short squeeze)** |

| HFT 视角 |
|----------|
| **Stock loan recall**、**hard-to-borrow fee spike** |
| **Funding rate**（crypto perp basis） |
| **Dividend / ex-date** 模型错误 |

---

## 4. 市场功能与竞争

### 4.1 套利机会两大成因 × 套利者角色

| 成因 | 套利者角色 |
|------|------------|
| **价格调整缓慢 (Slow price adjustment)** | **纪律执行者 (Disciplinarians)** — 共同因素变，部分价格 **滞后** → **强制纠正** 定价错误 |
| **不知情流动性需求** | **流动性搬运工 (Porters of liquidity)** — 一市场价格 **被推偏** → 从 **另一市场搬流动性** 过来 |

→ [Ch 14 不知情 flow](./chapter-14-买卖价差.md) · [Ch 9 公共益处](./chapter-09-好市场.md)

### 4.2 与做市商的关系

| | 做市商 (Dealer) | 套利者 |
|---|-----------------|--------|
| **连接维度** | 跨越 **时间** — 库存连接买卖 |
| **连接维度** | 跨越 **空间（市场）** — 对冲组合连接 **不同 venue/工具** |
| **关系** | **竞争** — 都赚 **mispricing**，维度不同 |

**无意功能：** 强制执行 **一价定律 (Law of one price)** — 整合 **分散的市场碎片**。

| HFT 视角 |
|----------|
| **Multi-venue HFT** — 同时 **MM + arb**；须分清 **PnL 来源** |
| **SIP vs direct feed** — arb 连接 **NBBO 碎片** |
| **Crypto CEX–DEX** — porter 角色 **跨链/跨所** |

---

## 5. 知情四类定位（Ch 10 回顾）

| 类型 | 信息 | HFT 典型 |
|------|------|----------|
| Value | 绝对 V | 少（慢） |
| News | ΔV | Latency |
| Info-tech | 他人错误 | Short-horizon pattern |
| **Arb** | **相对 mispricing** | **Basis、stat arb、pairs** |

---

## 6. 本章总结

| 要点 | 含义 |
|------|------|
| **定义** | 相对价值；买便宜卖贵，赌 **收敛** |
| **工具** | Hedge portfolio · basis · arbitrage spread vs band |
| **Pure vs Risk arb** | 均值回归有机制 vs 非平稳但短期回归 |
| **四风险** | 执行 · 基差/杠杆 · 模型 · 持有成本 |
| **角色** | Disciplinarian + Porter of liquidity |
| **vs Dealer** | 空间 vs 时间；共同维护 **价格一致性** |

> **HFT 读者 takeaway：** 多腿策略 **第一风险是 implementation（冰块探险者）**，第二风险是 **basis blowout + 杠杆（LTCM）**。`orderbook.go` 单所撮合只是 **一腿** — 真 arb 是 **跨 book 的 band 监控 + 同步 execution**。Ch 10–17 **知情分册** 收束；下一章 [Ch 18 买方交易者](./chapter-18-买方交易者.md) 转向 **机构 flow** 视角。

---

## 相关章节

- 上一章：[chapter-16-价值交易者.md](./chapter-16-价值交易者.md)
- 下一章：[chapter-18-买方交易者.md](./chapter-18-买方交易者.md)
- 知情总论：[chapter-10-知情交易者与市场效率.md](./chapter-10-知情交易者与市场效率.md)
- 做市（时间维度）：[chapter-13-做市商.md](./chapter-13-做市商.md)
- 价差与成本：[chapter-14-买卖价差.md](./chapter-14-买卖价差.md)
