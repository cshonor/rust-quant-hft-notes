# Ch 14 买卖价差 · Bid/Ask Spreads

> **Trading and Exchanges** · Larry Harris · **精读** · Part IV

本章深入剖析 **决定买卖价差宽窄的因素**，以及价差如何影响 **交易者策略与盈亏**。

> **Harris 全书最重要的一课（作者原话）：** **理解为什么不知情交易者总会亏损。**

> **HFT 核心章：** spread 分解、**Glosten-Milgrom**、maker/taker 权衡、**flow toxicity**；与 [Ch 13](./chapter-13-做市商.md)、[Ch 10](./chapter-10-知情交易者与市场效率.md)、[Ch 4 订单类型](./chapter-04-交易指令与订单类型.md)、[00-practice-go-dex M3](./00-practice-go-dex/notes/milestone-03-价差与流动性/) 直接衔接。

---

## 0. 为什么本章至关重要

| 读者 | 收获 |
|------|------|
| **零售 / 机构 taker** | 明白 **spread 不是随机收费** — 含 **逆向选择保险** |
| **做市商 / HFT maker** | 知道 **加宽什么、何时收窄** |
| **系统设计者** | **均衡价差** 由 **信息、波动、效用型兴趣** 共同决定 |

---

## 1. 价差的本质与竞争机制

### 1.1 即时性的价格

**买卖价差 (Bid-ask spread)** = 不耐烦交易者购买 **即时性 (Immediacy)** 所付的价  
= 做市商与 **限价单提供者** 因提供即时性而获得的 **补偿**。

| 支付方 | 收取方 |
|--------|--------|
| **Taker**（市价 / marketable limit） | **Maker**（dealer / standing limit） |

### 1.2 完全竞争市场的约束

竞争激烈、**自由进出** 的做市市场 → 价差 **自我调节**：

| 价差状态 | 结果 |
|----------|------|
| **过大** → 超额利润 | 新做市商 **进入** → 竞争 **收窄** |
| **过小** → 亏损 | 部分退出 → 幸存者 **加宽** |

**均衡：** 价差稳定在使做市商 **刚好获得正常利润** 的水平。

| HFT 视角 |
|----------|
| **Many HFT makers** on liquid names ≈ 竞争均衡 → **极窄 spread** |
| **Illiquid / toxic** names — makers **退出** → spread **宽** 或 **无做市** |

---

## 2. 价差的两大组成部分 (Spread Components)

| 成分 | 别名 | 含义 | 价格效应 |
|------|------|------|----------|
| **交易成本成分** | **暂时性价差 (Transitory)** | 补偿 **正常经营成本**（融资、人力、清算等） | 价格在 bid/ask 间 **来回跳动** — **Bid/ask bounce** |
| **逆向选择成分** | **永久性价差 (Permanent)** | 补偿 **输给知情者** 的预期损失；从 **不知情者** 多收以 **交叉补贴** | 成交后 mid **单向漂移** — [Glosten-Milgrom](https://en.wikipedia.org/wiki/Glosten%E2%80%93Milgrom_model) 订单流更新信念 |

### 2.1 交易成本 / 暂时性成分

- 覆盖 **可预测、可分摊** 的运营成本
- 价格在 spread 内 **均值回归** — 不构成长期 adverse move

### 2.2 逆向选择 / 永久性成分

- 做市商与知情者交易 → **低卖高买** → **系统性亏**
- 须 **加宽 spread**，从 **不知情 taker** 多收 → **弥补** informed 损失
- 做市商根据 **订单流** **更新对基本面的预期**

→ [Ch 13 §4.2](./chapter-13-做市商.md)

| HFT 视角 |
|----------|
| **Realized spread vs effective spread** 分解 — 暂时 vs 永久 |
| **Markout analysis**（成交后 1s/5s/60s mid move）量化 adverse selection |
| **VPIN** 等高 toxicity 代理 ↑ → **permanent component** ↑ |

---

## 3. 本书最重要的一课：不知情交易者为何总是亏损？

**残酷结论：** 无论用 **何种指令类型**，不知情者 **只要参与交易** → **最终输给知情者**。

### 3.1 使用限价单 (Limit Orders)

| 情形 | 结果 |
|------|------|
| 报价 **过高/过低** | 知情者 **迅速成交** → **事后后悔** (winner's curse) |
| 价格向 **有利方向** 变动 | 知情者 **不来成交** → 单 **挂着不 fill** → **错失** — 同样后悔 |

> 挂限价单 = **直接暴露于逆向选择** — [Ch 4 免费期权](./chapter-04-交易指令与订单类型.md)

### 3.2 使用市价单 (Market Orders)

| 保证 | **成交** |
|------|----------|
| 代价 | 付 **全 spread** |
| 隐含 | Spread 含 **逆向选择成分** → 不知情者 **替做市商承担** 防 informed 的 **保险成本** |

```
不知情参与者
    ├── 限价单 → 被 pick off 或 不成交后悔
    └── 市价单 → 付 spread（含 adverse selection 保费）
            └── 无论如何 → 系统性补贴知情者 + 做市商正常利润
```

| HFT 视角 |
|----------|
| **Retail flow** 常被视为 **less informed** — **PFOF / internalization** 围绕此定价 |
| 若你 **无 edge** 却频繁 taker → 本章描述的 **结构性亏损** |
| **Edge 定义**：你必须是 **informed / arb / 更快 flow router** 之一，而非「普通参与者」 |

---

## 4. 指令驱动市场中的均衡价差

**无传统做市商**、仅 **公众交易者** 的 **连续拍卖** 市场：

### 4.1 均衡调节

| 价差 | 行为 | 反馈 |
|------|------|------|
| **太宽** | 市价单太贵 → 全改 **限价单** 供流动性 | 竞争 → **收窄** |
| **太窄** | 限价单无利可图 → 全改 **市价单** 取流动性 | **扩大** |

### 4.2 限价单的「择时期权 (Timing Option)」

提交限价单 = 赋予市价单交易者 **宝贵择时期权**：

- 情况变化时（如价值上涨），taker 可 **立即** 以 **原限价** 成交
- 管理和撤销限价单有 **时间成本**

→ **均衡 spread 须足够宽**，补偿 LP **让渡择时期权** 的风险

| HFT 视角 |
|----------|
| **Cancel latency** 越长 → timing option 越大 → **equilibrium spread 越宽** |
| **Post-only / maker-only** 规则改变 **谁持有 option** |
| Go DEX M3：测 **spread 与 fill rate** 的 trade-off |

---

## 5. 决定价差的三大主要因素 (Primary Determinants)

| # | 因素 | 机制 | 对价差 |
|---|------|------|--------|
| **1** | **信息不对称 (Asymmetric information)** | 信息差距大 → **逆向选择** ↑ | **更宽** |
| **2** | **波动性 (Volatility)** | 限价单 **择时期权** 价值 ↑；**库存风险** ↑ | **更宽** |
| **3** | **效用型交易兴趣 (Utilitarian trading interest)** | 投资/对冲/借贷等 **真实需求** ↑ → 固定成本 **分摊**；不知情单 **稀释** 知情比例 | **更窄** |

```
Spread ≈ f(信息不对称, 波动性, 效用型兴趣)
         宽 ←———|———→ 窄
```

→ 波动性专章 [Ch 20](./chapter-20-波动性.md) · 流动性 [Ch 19](./chapter-19-流动性.md)

| HFT 视角 |
|----------|
| **Earnings、FOMC、并购** → (1)(2) ↑ → **widen or pull** |
| **Index rebalance、month-end hedging** → (3) ↑ → **can tighten** if not toxic |
| **Maker model inputs**：vol, toxicity, utilitarian calendar |

---

## 6. 次要决定因素与代理变量 (Secondary Proxies)

信息不对称与效用型兴趣 **难直接度量** → 用 **可观察特征** 预测价差：

### 6.1 倾向更窄价差

| 特征 | 原因 |
|------|------|
| **大盘股 / 大公司** | 活跃、信息 **公开** |
| **严格披露规则** | 降低信息差 |
| **分析师 / 媒体覆盖多** | 信息 **分散** |
| **广泛指数成分** | 比单一股票 **信息不对称低** |
| **成熟行业** | 比新兴行业 **易估值** |

### 6.2 倾向更宽价差

| 特征 | 原因 |
|------|------|
| **高波动** | 期权价值 + 库存风险 |
| **天气敏感商品**（如橙汁期货） | 基本面 **难预测** |
| **缺乏透明度的新公司** | 信息差大 |
| **财报前夕** | 预期 **重大信息不对称** |

| HFT 视角 |
|----------|
| **Universe selection** — HFT 常 **避开** spread 过宽 / 失灵边缘标的 |
| **Event calendar** 驱动 **intraday spread schedule** |

---

## 7. 市场失灵 (Market Failure)

| 条件 | 结果 |
|------|------|
| 信息不对称 **极严重** | 做市商预期 **informed 损失 > spread 收入** |
| 或效用型兴趣 **极低** | **拒绝做市** |
| 表现 | 价差宽到 **无交易** |

**后果：** 许多小企业 **无法在公开市场发股** → 依赖 **VC / 银行贷款**（尽调与监控克服信息差）

| HFT 视角 |
|----------|
| **Penny stocks、部分 crypto pairs** — **流动性蒸发** |
| **Circuit breaker / halt** — 临时 **失灵** |
| 与 [Ch 9 好市场](./chapter-09-好市场.md) — 无 utility flow → 市场 **不存在** |

---

## 8. 指令类型 × 价差（总表）

| 角色 | 指令 | 主要付什么 | 主要风险 |
|------|------|------------|----------|
| 不知情 taker | 市价 | 全 spread（含 adverse selection） | 显性成本 |
| 不知情 maker | 限价 | 免费期权 + 逆向选择 | pick off / 不成交 |
| 知情 taker | 市价 | spread | 信息半衰期 — 快过期则仍赚 |
| 知情 maker | 限价 | 较少（若真 informed） | 较少被 pick off |
| Dealer | 双边报价 | — | spread 收入 − adverse selection − inventory |

---

## 9. 本章总结

| 要点 | 含义 |
|------|------|
| **Spread = immediacy 的价格** | 竞争市场 **自我调节** 至正常利润 |
| **两成分** | **暂时性**（成本、bounce）+ **永久性**（adverse selection） |
| **最重要一课** | **不知情者参与即亏** — 限价与市价 **路径不同，结局相似** |
| **Order-driven 均衡** | 太宽→全 limit；太窄→全 market；+ **timing option** |
| **三要素** | 信息差 ↑、波动 ↑ → 宽；效用型兴趣 ↑ → 窄 |
| **失灵** | 做市无利可图 → **无交易** |

> **HFT 读者 takeaway：** 你的 **maker 模型** 是在估计 **两成分**；你的 **alpha** 必须超过 **不知情者的结构性税**。读 `orderbook.go` 时 — **best bid/ask 差距** 不是常数，而是 **信息 × 波动 × flow 组成** 的均衡结果。M3 练手建议：对同一撮合引擎，模拟 **toxic vs benign flow** 下 **均衡 spread 该如何变**。

---

## 相关章节

- 上一章：[chapter-13-做市商.md](./chapter-13-做市商.md)
- 下一章：[chapter-15-大宗交易者.md](./chapter-15-大宗交易者.md)
- 知情与不知情：[chapter-10-知情交易者与市场效率.md](./chapter-10-知情交易者与市场效率.md) · [chapter-08-为什么人们要交易.md](./chapter-08-为什么人们要交易.md)
- 订单与期权：[chapter-04-交易指令与订单类型.md](./chapter-04-交易指令与订单类型.md)
- 流动性：[chapter-19-流动性.md](./chapter-19-流动性.md) · 波动性：[chapter-20-波动性.md](./chapter-20-波动性.md)
- 练手：[00-practice-go-dex M3 价差与流动性](./00-practice-go-dex/notes/milestone-03-价差与流动性/)
