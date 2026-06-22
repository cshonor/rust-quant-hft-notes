## 6.4.1–6.4.4 Cache 组织与映射

### 6.4.1 通用组织结构

地址划分为（从低位到高位）：

```
| block offset (b) | set index (s) | tag (t) |
```

- **S = 2^s** 组，每组 **E** 条 cache line，每条 **B = 2^b** 字节
- 查 cache：**index 选组 → tag 比较 → valid 位**

### 6.4.2 直接映射 (E=1)

- 每组 **一条** line — 实现简单
- **冲突 miss (conflict miss)：** 多个不同块映射到 **同一组**，互相踢出

```
组 i 只能放 1 个块 — 交替访问 A、B 同组 →  thrashing
```

### 6.4.3 组相联 (1 < E < S)

- **E 路组相联** — 工业界 L1/L2 常见（如 8-way）
- 降低冲突 miss，硬件成本适中

### 6.4.4 全相联 (S=1)

- **一组、E 条 line** — 全 tag 比较，贵，用于 **小 cache**（TLB、部分 L1）

**HFT 直觉：**

- **数据布局** 导致多 hot 结构映射到同一 LLC set → 罕见但可 profile
- **对齐到 cache line (64B)** 避免一 struct 跨两条 line 双倍 load

---

← [本章导读](../README.md)
