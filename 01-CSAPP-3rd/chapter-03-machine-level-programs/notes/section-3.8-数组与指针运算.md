## 3.8 数组分配和访问

### 3.8.1 基本原则

- 数组元素 **连续存放**；`T A[N]` 大小 `N * sizeof(T)`
- 访问 `A[i]` → 基址 + `i * sizeof(T)` — 汇编里常见 `(%base,%idx,scale)`

### 3.8.2 指针运算

```c
int *p = A;
*(p + i)  // 等价 A[i]；p+i 按 sizeof(int) 缩放
```

- **指针减法** 得元素个数（同类型、同数组内）

### 3.8.3 嵌套数组

`A[i][j]` 行主序：`&A[i][j] = A + (i * N + j) * sizeof(T)`

### 3.8.4 定长数组 vs 3.8.5 变长数组 (VLA)

- 定长 — 栈或全局；大小编译期可知
- **VLA** — C99，栈上 `alloca` 式分配；**HFT 热路径避免**（不可预测栈扩展、GCC 扩展）

### HFT 布局

| 模式 | 说明 |
|------|------|
| **SoA** (Structure of Arrays) | 同字段连续 — SIMD、顺序扫描友好 |
| **AoS** (Array of Structures) | 对象导向 — 单条记录局部性好 |
| **Ring buffer** | 定长数组 + 头尾指针 — 行情队列标配 |

→ cache 与局部性：[Ch 6](../../chapter-06-memory-hierarchy/) · [Ch 1.5](../chapter-01-tour-of-computer-systems/notes/section-1.5-高速缓存至关重要.md)

---

← [本章导读](../README.md)
