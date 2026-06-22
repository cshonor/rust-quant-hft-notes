## 6.5–6.6 缓存友好代码与存储器山

### 6.5 编写高速缓存友好的代码

**原则：**

1. **重复引用相同数据** — 时间局部性（内层循环复用）
2. **步长为 1 的顺序访问** — 空间局部性
3. **控制工作集** — fit in cache；太大则 capacity miss

**反模式：**

```c
// 差：按列扫二维数组（stride = N）
for (j = 0; j < N; j++)
    for (i = 0; i < N; i++)
        sum += a[i][j];

// 好：按行扫
for (i = 0; i < N; i++)
    for (j = 0; j < N; j++)
        sum += a[i][j];
```

**HFT 结构选择：**

| 场景 | 倾向 |
|------|------|
| 逐 tick 扫全价位 | **数组/vector** 连续 |
| 稀疏更新价位 | 哈希/树 + **节点池**（避免 scatter malloc） |
| 多字段批处理 | **SoA** |
| 单条记录热更新 | **AoS** 或紧凑 struct |

### 6.6.1 存储器山 (Memory Mountain)

- 二维测试：**读数组** 随 **stride** 与 **working set** 变化测 **读吞吐 (MB/s)**
- **山脊** — stride 小 + working set < cache → 高吞吐
- **平地/悬崖** — 超出 L3 → 吞吐骤降

**实验（原书 `mountain`）：** 亲眼见 **stride 8 元素 vs 1 元素** 差一个数量级。

### 6.6.2 重新排列循环提高空间局部性

- **矩阵乘、卷积、order book 批量统计** — 循环顺序决定性能
- 编译器 `-O3` 可能自动 **循环交换 (interchange)**，但别完全依赖

### 6.6.3 在程序中利用局部性

- **分块 (blocking/tiling)** — 使子块 fit L1/L2
- **融合 (fusion)** — 多次扫合并成一次（减总带宽）
- **预取** — 软件 `__builtin_prefetch` 对 predictable stride

**HFT 工作流：**

```
改布局/循环 → microbench (CPE/MB/s) → perf cache-misses → 端到端 P99
```

### 6.7 小结（原书）

存储器是 **层次 + 局部性**；程序员通过 **数据结构与访问模式** 决定 miss rate — 往往比换 CPU 频率更有效。

→ 工具：`csim` 模拟 cache（课程）；生产用 `perf` + [Ch 5 profile](../chapter-05-optimizing-performance/notes/section-5.13-5.15-剖析与实战优化.md)

---

← [本章导读](../README.md)
