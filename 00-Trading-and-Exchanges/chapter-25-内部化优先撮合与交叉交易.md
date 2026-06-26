# Ch 25 内部化、优先分配与内部交叉撮合 · Internalization, Preferencing, and Crossing

> **Trading and Exchanges** · Larry Harris · **精读** · Part VII

本章探讨经纪人 **不把订单发往公开市场**，而在内部消化或 **出售给特定交易商** 时的 **经济学与监管问题** — 导致交易偏离中央交易所 → **市场碎片化 (Market Fragmentation)**。

> **HFT 读者：** **PFOF、wholesale internalizer、dark pool、retail vs institutional flow toxicity** 的主线；与 [Ch 7](./chapter-07-经纪人.md)、[Ch 24 撇奶油](./chapter-24-专家做市商系统.md)、[Ch 6 交叉网络](./chapter-06-指令驱动市场.md)、[Ch 14](./chapter-14-买卖价差.md)、[Ch 26](./chapter-26-市场内与市场间的竞争.md) 衔接。

---

## 0. 本章主线

```
三种截留方式（内部化 · 优先分配 · 内部交叉）
        ↓
Best execution 争议 + 零售经济学（PFOF）
        ↓
公开市场 toxicity ↑、spread 变宽、权力转移
        ↓
监管权衡：散户净成本 vs 中央市场流动性
```

---

## 1. 三种主要的订单截留方式

| 方式 | 英文 | 机制 |
|------|------|------|
| **内部化** | Internalization | 经纪人兼 **dealer**，用 **自有资金 / 库存** 填补客户订单 |
| **优先分配** | Preferencing | 将客户 **市价单** **定向路由** 给特定交易商，换取 **金钱或非金钱补偿** → **订单流支付 (PFOF)** |
| **内部交叉撮合** | Internal order crossing | 经纪人或 **ECN** 在 **自有系统内** 将客户 **买 vs 卖** **直接匹配** |

→ [Ch 7 §3 PFOF](./chapter-07-经纪人.md) · [Ch 6 衍生定价交叉网](./chapter-06-指令驱动市场.md)

| HFT 视角 |
|----------|
| **Wholesaler (Citadel/Virtu 等)** — preferencing 的 modern 主体 |
| **Broker-dealer internalization** — Robinhood 类模型 |
| **ATS / dark pool crossing** — 机构 internal cross |
| **Lit HFT MM** 吃的是 **被「扔回」市场的 toxic flow** |

---

## 2. 最佳执行 (Best Execution) 的争议

### 2.1 利益冲突

经纪人 **内部化** 或 **收 PFOF** → [Ch 7 委托代理](./chapter-07-经纪人.md) **严重冲突** — 客户与监管质疑是否 **尽最佳执行义务**。

### 2.2 什么是最佳执行？

| 维度 | 不仅 **价格**，还有 **速度、成交确定性** |
|------|----------------------------------------|
| **美国常见主张** | 在 **NBBO** 成交 = best execution |
| **掩盖** | 发往公开市场可能获得的 **价格改善 (Price improvement)** |

→ [Ch 21 TCA](./chapter-21-流动性与交易成本衡量.md) · **IS vs NBBO**

| HFT 视角 |
|----------|
| **606 reports、Reg NMS Rule 605** — 披露与度量 |
| **Price improvement** 统计 — wholesaler 营销核心 |
| **NBBO 仅 top-of-book** — 深度改善不在 NBBO 内 |

---

## 3. 零售客户的困境：低佣金 vs 劣质执行

### 3.1 散户为何只看佣金？

| 可观察 | **佣金** — 容易比较 |
|--------|---------------------|
| **难观察** | **执行质量**（price improvement、延迟、部分成交） |

→ 倾向选 **佣金最低** 的经纪人。

### 3.2 订单流的价值

| 交易商渴望零售单 | 散户多为 **不知情交易者** [Ch 8](./chapter-08-为什么人们要交易.md) |
|----------------|---------------------------------------------------------------------|
| **原因** | 与零售成交 → **低逆向选择** → **丰厚 spread** |

→ [Ch 14 不知情补贴](./chapter-14-买卖价差.md) · [Ch 24 cream-skimming](./chapter-24-专家做市商系统.md)

### 3.3 竞争市场的结果

| 批发市场（完全竞争） | 交易商争 **安全高利润** 零售单 → **高 PFOF** 给经纪人 |
|----------------------|------------------------------------------------------|
| 零售市场（完全竞争） | 经纪人争散户 → 用 PFOF **补贴** → **极低佣金** |

```
Retail uninformed flow  →  高 value to wholesaler
        ↓
PFOF to broker  →  low commission to retail
```

| HFT 视角 |
|----------|
| **Payment for order flow** 经济学 — 非「贿赂」简单叙事，是 **竞争均衡** |
| **Zero-commission** 经纪 **商业模式** 读本 |
| **Institutional lit flow** 与 **retail internalized** **分流** |

---

## 4. 市场权力转移与流动性受损

### 4.1 公开市场价差变宽

| 机制 | 最安全 **不知情** 零售单被 **截留 / preferenced** |
|------|--------------------------------------------------|
| **结果** | 进入 **公开市场** 的订单中 **知情比例上升**（wholesaler 把 **不要的危险单** 扔给市场） |
| **反应** | 公开做市商与限价单交易者 **拉宽 spread** 自保 |

→ [Ch 14 信息不对称 ↑](./chapter-14-买卖价差.md)

| HFT 视角 |
|----------|
| **Lit market toxicity ↑** — VPIN、adverse selection 模型 |
| **Retail off-exchange %** 与 **lit spread** 实证关联 |

### 4.2 伤害公共限价单交易者

| 剥夺 | 公共 LP 与 **不知情散户** 成交的机会 |
|------|-------------------------------------|
| **后果** | **降低挂单动机** — 市场权力 **从公共限价单 → 交易商** |

→ [Ch 19 谁在供流动性](./chapter-19-流动性.md)

### 4.3 经纪人的双赢：内部交叉

| 内部交叉 | 买卖双方 **同一经纪人客户** 匹配 |
|----------|--------------------------------|
| **收入** | 常可从 **双方收佣金** |

| HFT 视角 |
|----------|
| **Dual agency crossing** — 冲突与披露 |
| **Dark pool** 作为 **internal cross at scale** |

---

## 5. 监管的权衡 (Regulatory Trade-offs)

| 受益方 | 部分交易者 — **低佣金 + 净 price improvement** 的散户 |
|--------|------------------------------------------------------|
| **受损方** | **中央市场流动性**、**价格发现**、[Ch 9 公共益处](./chapter-09-好市场.md) |

### 5.1 完全合并中央 LOB？

| 主张 | **Consolidated limit order book (CLOB)** — 强迫所有订单 **同一地点** |
|------|---------------------------------------------------------------------|
| **反对完全禁止** | 切断 **保密性、执行速度** 等特殊服务渠道 — [Ch 18 隐蔽](./chapter-18-买方交易者.md) |

### 5.2 权衡小结

```
散户净成本可能更低（佣金 ↓ 抵消部分 spread ↑）
        ‖
公开市场 LP 受损、toxicity ↑、碎片化
```

| HFT 视角 |
|----------|
| **Reg NMS、MEMX、IEX** — 碎片化与 **trade-through** 规则 |
| **Maker in lit** 需理解 **flow 被抽走** 的结构性原因 |
| **Segmentation** — retail / institutional / lit **不同 microstructure** |

---

## 6. 三种方式对照

| | 谁成交 | 经纪人激励 | 典型 flow |
|---|--------|------------|-----------|
| **Internalization** | 经纪人自营库存 | 价差 + 不必付外部 | 零售市价 |
| **Preferencing / PFOF** | 指定 wholesaler | **PFOF 收入** | 零售市价 |
| **Internal crossing** | 两客户内部对敲 | **双边佣金** | 可零售可机构 |

---

## 7. 与 Ch 24 专家制度

| Ch 24 Specialist | Ch 25 |
|------------------|-------|
| 见订单来源 **cream-skim** | **PFOF 路由** cream-skim **制度化** |
| Stop stock / look-back | **Internalization at NBBO** |
| 交易所内特权 | **场外 / 并行市场** 特权 |

---

## 8. 本章总结

| 要点 | 含义 |
|------|------|
| **三种截留** | Internalization · Preferencing (PFOF) · Crossing |
| **Best ex** | 难定义；NBBO 可能 **掩盖** improvement |
| **零售经济学** | 只看佣金 → PFOF 均衡 → **极低佣金** |
| **公开市场** | 不知情单被抽走 → **toxicity ↑** → **spread 宽** |
| **权力转移** | 公共 LP → **交易商 / wholesaler** |
| **监管** | 散户净成本 vs **CLOB / 价格发现** |

> **HFT 读者 takeaway：** 你在 **lit 做市** = 往往吃 **被 wholesaler 筛过的 residual flow** — 须 **更宽 adverse selection 成分**，而非抱怨「散户太精」。理解 PFOF 后，**segment strategy**：服务 **internalized retail**（wholesale 侧）vs **toxic lit**（不同模型）。下一章 [Ch 26](./chapter-26-市场内与市场间的竞争.md) — **碎片化** 的venue竞争全景。

---

## 相关章节

- 上一章：[chapter-24-专家做市商系统.md](./chapter-24-专家做市商系统.md)
- 下一章：[chapter-26-市场内与市场间的竞争.md](./chapter-26-市场内与市场间的竞争.md)
- 经纪人：[chapter-07-经纪人.md](./chapter-07-经纪人.md)
- 价差与不知情：[chapter-14-买卖价差.md](./chapter-14-买卖价差.md)
- 交叉网络：[chapter-06-指令驱动市场.md](./chapter-06-指令驱动市场.md)
- 好市场：[chapter-09-好市场.md](./chapter-09-好市场.md)
