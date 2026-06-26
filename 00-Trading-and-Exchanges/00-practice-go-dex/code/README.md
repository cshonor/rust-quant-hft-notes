# Go DEX 练手 · 源码

独立 **Go module**，与 Harris 理论目录分离；从 **M1** 起按 [OUTLINE](../OUTLINE.md) 增量提交。

## 常用命令

在 `code/` 目录下：

```bash
make        # 默认跑 test
make build  # 编译 → bin/exchange
make run    # build 后运行入口（打印 working）
make test   # go test -v ./...
```

无 `make` 时可直接：`go build -o bin/exchange ./cmd/exchange`，再执行 `bin/exchange`（Windows 为 `bin/exchange.exe`）。

## 包布局（随里程碑扩展）

```
code/
├── go.mod
├── Makefile
├── order/          # M1：Order, Side, Type
├── book/           # M1：OrderBook, BestBid/Ask, TakeMarket
├── match/          # M2：Matcher, Trade（待建）
├── metrics/        # M3：Spread, Depth（待建）
└── cmd/
    └── exchange/   # 程序入口（先跑通，M4 可扩展 HTTP）
```

## 与理论对照

| 包 | Harris | 状态 |
|----|--------|------|
| `order`, `book` | Ch 4–5 | M1 ✅ |
| `match` | Ch 6 | M2 |
| `metrics` | Ch 13–14, 19 | M3 |

实践笔记 → [../notes/](../notes/)
