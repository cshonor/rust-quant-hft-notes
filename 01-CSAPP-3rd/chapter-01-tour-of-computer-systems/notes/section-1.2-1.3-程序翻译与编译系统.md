## 1.2–1.3 程序翻译与编译系统

### 1.2 程序被其他程序翻译成不同格式

从 `hello.c` 到能在机器上跑，要经过 **编译系统（compilation system）** 多步翻译 — 每一步都在换 **上下文**（源码 → 汇编 → 机器码 → 可执行）：

```
hello.c  ──预处理器──►  hello.i（展开 #include/#define）
         ──编译器──►    hello.s（汇编文本）
         ──汇编器──►    hello.o（目标文件，机器码 + 符号表）
         ──链接器──►    a.out（可执行，含 CRT、libc 等）
```

| 阶段 | 输入 | 输出 | 工具 |
|------|------|------|------|
| 预处理 | `.c` | `.i` | `cpp` / `gcc -E` |
| 编译 | `.i` | `.s` | `cc1` / `gcc -S` |
| 汇编 | `.s` | `.o` | `as` |
| 链接 | `.o` + 库 | 可执行 | `ld` / `gcc` |

**静态链接 vs 动态链接：** 可执行可嵌入 libc，或运行时加载 `libc.so` — HFT 生产常静态/部分静态以减少依赖与启动不确定性（→ [Ch 7 链接](../../chapter-07-linking/)）。

### 1.3 了解编译系统如何工作是大有益处的

**为何要懂：**

- **优化** — `-O2/-O3`、LTO、PGO 改的是哪一阶段产物
- **调试** — 崩溃栈、符号、行号对应哪层翻译
- **链接错误** — undefined reference、ODR、ABI 不匹配
- **安全/合规** — 可重现构建

---

### 量化场景映射 · 编译链 ↔ 策略生命周期

把 CSAPP 编译链和以后写策略/引擎对照记 — **同一条「从文本到跑起来」的链**：

| 编译链环节 | 在干什么 | 量化 / DeFi 类比 |
|------------|----------|------------------|
| **预处理** `#include` / `#define` | 文本替换、头文件展开 | **策略参数注入**：把 `MAX_POSITION`、`SYMBOL_LIST` 从 config/宏写进编译期或代码 |
| **编译** `.c` → `.s` | 高级逻辑 → 汇编 | **策略逻辑 → 可执行决策**：信号计算、风控规则变成 CPU 会执行的指令 |
| **汇编** `.s` → `.o` | 助记符 → 机器码 | **定稿 hot path**：哪几段汇编是 tick 内必须跑完的 |
| **链接** `.o` + 库 → 可执行 | 拼模块、解析符号 | **集成**：行情解码库 + 订单网关 + 日志 + 你的 alpha 链成一个 binary |
| **加载运行** `execve` | OS 映射进内存、跳 `_start` | **实盘启动**：pin 核、连 feed、进入主循环收行情 |

```
config.yaml / 宏参数     ≈  预处理
策略 C++ 源码            ≈  .c
Release -O3 -march=native ≈  编译+汇编
链 libfix + libmd        ≈  链接
systemd 拉起 pinned 进程  ≈  execve 加载运行
```

**和 1.1 的「上下文」：** 源码里 `price > threshold` 是 **C 语法上下文**；编译后是 **指令上下文**；线上 tick 里是 **协议字段上下文** — 三条链最终在 **同一进程、同一 CPU** 上会合。

---

### 动手实验 · hello.c 走一遍编译链

**1. 准备最小程序**

```c
// hello.c
#include <stdio.h>
int main() {
    printf("hello, world\n");
    return 0;
}
```

**2. 看 gcc 背后调了谁（推荐第一次做）**

```bash
gcc -v hello.c -o hello 2>&1 | less
```

输出里能看到：`cc1`（编译）→ `as`（汇编）→ `collect2`/`ld`（链接），以及 `-L` 库搜索路径。建立直觉：**gcc 是驱动，不是单独一个程序**。

**3. 分阶段产物（建议每步 `-o` 打开看一眼）**

```bash
gcc -E hello.c -o hello.i          # 预处理：stdio.h 展开成几千行
gcc -S hello.c -o hello.s          # 汇编：搜 main、call printf
gcc -c hello.c -o hello.o          # 目标文件：机器码，人眼不可读
file hello.o                       # ELF 64-bit relocatable
gcc hello.o -o hello               # 链接：拉进 crt、libc
./hello
```

**4. 看机器码与反汇编（和 1.1「同一比特不同上下文」呼应）**

```bash
objdump -d hello.o | less          # 未链接：call 还是 rel 占位
objdump -d hello | less            # 链接后：完整 main 反汇编
```

**5. 和量化相关的两个延伸（可选）**

```bash
gcc -O0 -S hello.c -o hello-O0.s
gcc -O3 -S hello.c -o hello-O3.s
diff -u hello-O0.s hello-O3.s      # 看优化如何改「指令上下文」

gcc -g hello.c -o hello && gdb ./hello
# (gdb) break main → run → disassemble  # 源码行 ↔ 汇编 ↔ 地址
```

**Checklist（做完打勾）：**

- [ ] 能说出 `.i` / `.s` / `.o` / 可执行各是什么上下文
- [ ] `gcc -v` 里见过 `cc1`、`as`、`collect2`
- [ ] 用 `objdump -d` 看过 `main` 至少一条 `call`

---

### HFT 构建注意

- **Release flags 在 CI 与生产一致** — `-march=native`、LTO、`-DNDEBUG`
- **链接方式** — whole-archive 静态库 vs `dlopen` 插件 → 启动延迟与页 fault（→ [Ch 7](../../chapter-07-linking/)、[Ch 9](../../chapter-09-virtual-memory/)）
- **行情解码** — 协议 `.h` 里 struct layout 要和 spec 逐字段对齐；改 spec = 改「协议上下文」，常要 **版本号分支**（回连 1.1）

---

← [本章导读](../README.md)
