## 6.3 存储器层次结构（6.3.1–6.3.2）

### 6.3.1 层次结构中的缓存

**核心思想：** 第 k+1 层是第 k 层的 **cache**，由硬件或软件管理。

```
L0 寄存器
L1 d-cache / i-cache
L2 统一 cache
L3 LLC（常多核共享）
主存
本地磁盘 / 远程存储
```

- **命中 (hit)** — 在上层找到
- **缺失 (miss)** — 向下层取，**惩罚 latency**
- **块 (block/line)** — 以块为单位搬移，利用空间局部性

### 6.3.2 概念小结

| 术语 | 含义 |
|------|------|
| **块大小 B** | 通常 64B |
| **相联度 E** | 每组几条 line |
| **组数 S** | 索引组数 |
| **容量** | ≈ S × E × B（简化） |

**AMAT (平均访问时间)：**

```
AMAT = HitTime + MissRate × MissPenalty
```

**HFT：** 优化目标常是 **降 miss rate** 或 **降 miss penalty**（如 NUMA 本地内存、prefetch）；`perf` 量化 miss。

→ [Ch 1.5 缓存直觉](../chapter-01-tour-of-computer-systems/notes/section-1.5-高速缓存至关重要.md)

---

← [本章导读](../README.md)
