## ④ 汇编与 C 的结合 · `io_hlt`

**一句话：C 写 OS 主逻辑；汇编只包 C 写不了或不该写的 CPU 专属操作，链接后 C 当普通函数调用。**

承前：[§3.3](./section-3.3-32-位模式前期准备与导入-C-语言.md) — 32 位下 **`HariMain`** 用 C 跑；本节解决 **「C 不够用时谁补」**。

---

### 为什么 C 不能直接写某些指令？

C 是 **可移植的高级语言** — 编译器要能在不同 CPU 上生成代码，**不会**为每一种芯片的特殊指令都提供语法。

| C 擅长 | C 搞不定（必须用汇编） |
|--------|------------------------|
| 算法、数据结构、业务逻辑 | **`HLT`** — 让 CPU 休眠 |
| 函数调用、循环、条件 | **写 CR0 / CR3 / MSR** — 开保护模式、开分页 |
| 大部分内存读写 | **切 16→32→64 位** 的那几条关键指令序列 |
| | **精确控制标志位、中断开关 `CLI/STI`** 等（裸机/OS 早期） |

**做法：** 汇编写 **独立函数或代码片段** → 链接器与 C **拼成同一个 bootpack** → C 里 **`io_hlt();`** 像调普通函数。

```
bootpack.c              asmfunc.asm
    │                       │
    │  void io_hlt(void);   │  io_hlt:
    │  … io_hlt(); …        │      HLT
    └───────────┬───────────┘      RET
                ▼
           链接 → bootpack 二进制
```

| 文件 | 后缀 | 职责 |
|------|------|------|
| **`bootpack.c`** | `.c` | **`HariMain`**、OS 主逻辑；**调用** `io_hlt()` 等 |
| **`asmfunc.asm`** | `.asm` | **`io_hlt`** 等 **底层原语** — 几条指令 + `RET` |
| **`nasmhead.asm`** | `.asm` | **切 VGA、开 A20、建 GDT、进 32 位** — 比 `io_hlt` 更大块，仍在 C 跑之前 |
| **`ipl.asm`** | `.asm` | **512 B 引导** — 全汇编，还没有 C 环境 |

**Day 3 工程分层：**

```text
ipl.asm（16 位，512B）     读盘 — 尚无 C
    ↓
nasmhead.asm（16→32）      模式切换 — 仍必须汇编
    ↓
bootpack.c（32 位 C）      HariMain 主逻辑
    +
asmfunc.asm（32 位 asm）   io_hlt 等 C 调用的「补丁」
```

**你现在：** [ipl.asm](../code/ipl.asm) **全是汇编** — 还没走到 C；等 bootpack 链起来，就会 **`.asm` + `.c` 一起链接**。

---

### 典型例子：`io_hlt`

C 里没有「休眠这条 CPU 指令」的语句，只能：

**asmfunc.asm（示意）：**

```nasm
        BITS 32
        GLOBAL io_hlt

io_hlt:
        HLT
        RET
```

**bootpack.c（示意）：**

```c
void io_hlt(void);   /* 声明：实现在 asmfunc.asm */

void HariMain(void) {
    for (;;) {
        io_hlt();    /* 调用汇编包装 */
    }
}
```

| 谁 | 干什么 |
|----|--------|
| **C** | 决定 **什么时候** 休眠（主循环） |
| **汇编** | 执行 **HLT** 这一条 CPU 指令 |
| **链接器** | 把 `io_hlt` 的地址填进 C 的 `call` |

更大块的例子：**nasmhead** 里整段 **GDT + 切 CR0** — C 更写不了，所以整段留在 **`.asm`**，只有切完后 **`call HariMain`** 才交给 C。

---

### 完整例子：16 位切 32 位 + 调 C（汇编搭台，C 唱戏）

下面是一个 **能看清配合关系** 的极简模型（教学用；原书 **`HariMain`** 此处写 **`kernel_main`** 方便对照通用教程）。完整文件见 [code/example/](../code/example/)。

#### ① 汇编部分 — `nasmhead-minimal.asm`（≈ 原书 nasmhead）

**汇编负责：C 绝对写不了的「切模式 + 寄存器」**

```nasm
        BITS 16
switch_to_32:
        cli                         ; 关中断
        lgdt [gdt_desc]             ; 加载 GDT
        mov     eax, cr0
        or      eax, 1              ; CR0.PE = 1，开保护模式
        mov     cr0, eax
        jmp     CODE_SEL:init_pm    ; 远跳转，进入 32 位代码段

        BITS 32
init_pm:
        mov     ax, DATA_SEL        ; 数据段选择子
        mov     ds, ax
        mov     es, ax
        mov     ss, ax
        mov     esp, 0x90000        ; 栈 — C 函数调用需要

        extern  kernel_main
        call    kernel_main         ; ★ 舞台搭好，请 C 上场

hang:
        hlt
        jmp     hang
```

GDT 定义（8 字节描述符 × 3 项）省略 — 见 [code/example/nasmhead-minimal.asm](../code/example/nasmhead-minimal.asm)。

#### ② C 部分 — `kernel_main.c`（≈ 原书 bootpack.c / HariMain）

**C 负责：循环、字符串、业务逻辑 — 编译器自动生成 32 位机器码**

```c
void kernel_main(void) {
    volatile char *vidmem = (volatile char *)0xB8000;
    const char *str = "Hello 32-bit C!";
    int i;

    for (i = 0; str[i] != '\0'; i++) {
        vidmem[i * 2]     = str[i];
        vidmem[i * 2 + 1] = 0x07;
    }
    for (;;) { }
}
```

C **没有**「把 CR0 第 0 位置 1」的语句；**有** `for` 循环往显存写字 — 所以切模式归 asm，打印逻辑归 C。

#### ③ 怎么「拼」在一起？

```text
nasmhead-minimal.asm  ──nasm──►  nasmhead.o
kernel_main.c         ──gcc -m32──►  kernel_main.o
                                        │
                                        ld（链接器）
                                        ▼
                                   bootpack.elf
```

| 步骤 | 谁干 | 结果 |
|------|------|------|
| **汇编** | `nasm -f elf32 …` | `switch_to_32`、`init_pm`、`call kernel_main` 的机器码 |
| **编译 C** | `gcc -m32 -c …` | `kernel_main` 的机器码 |
| **链接** | `ld …` | 把 **`call kernel_main`** 里的地址 **填成 C 函数的真实入口** |

**执行顺序（运行时）：**

```text
switch_to_32（16 位 asm）
    → init_pm（32 位 asm：段、栈）
        → call kernel_main（跳进 C）
            → for 循环写 "Hello 32-bit C!"（C）
                → 若返回 → hang（asm 里 HLT）
```

#### ④ 和原书 haribote 的对应

| 教学示例 | 原书 Day 3 | 分工 |
|----------|------------|------|
| `switch_to_32` / GDT / CR0 | **nasmhead.asm** 前半 | 汇编搭台 |
| `call kernel_main` | 跳进 **`HariMain`** | asm → C 交接 |
| `kernel_main` 里写显存 | **bootpack.c** | C 唱戏 |
| （另文件）`io_hlt` | **asmfunc.asm** | C 调 asm **小补丁** |
| （更前）IPL 读盘 | **[ipl.asm](../code/ipl.asm)** | 尚无 C |

**记忆：** **汇编 = 搭台（切模式、栈、段、必要时 call C）** · **C = 唱戏（HariMain 及以后所有 OS 逻辑）** · **asmfunc = C 偶尔需要的几条指令外包**。

链接命令示意见 [code/example/README.md](../code/example/README.md)。

---
### 和嵌入式一样吗？

**大思路一样：底层汇编搭台，C 写上层。** 但 **OS 引导比常见嵌入式更「汇编-heavy」**。

| | **OS 引导（haribote / 本书）** | **嵌入式（常见 MCU）** |
|---|-------------------------------|-------------------------|
| **汇编** | IPL、nasmhead、asmfunc — **启动 + 切模式 + 指令补丁** | **startup.S / startup.asm** — 复位向量、设栈、拷 `.data`、跳 `main` |
| **C** | **`HariMain`** — 内核主体 | **`main()`** — 业务逻辑 |
| **链接** | 多个 `.o` → bootpack | 多个 `.o` → `.elf` / `.bin` |
| **比例** | 启动链 **大段必须是 asm** | 启动文件 often **几十到几百行 asm**，其余 **大量 C** |

**嵌入式常见模式：**

1. **上电** → 汇编 **startup**（栈、BSS、时钟最低配置）  
2. **`main()`** → 几乎全 C  
3. 偶尔 **`xxx_hal.asm`** 或内联 asm — 某条 sleep/wfi、关中断  

**高端芯片 / SDK：** 厂商把 startup、寄存器操作封进 **库 + 头文件**，你 **只写 C** — 底下仍是 **汇编或编译器内建**，只是 **别人写好了**。

**本仓库 HFT 线：** [00-practice-go-dex](../../../../00-Trading-and-Exchanges/00-practice-go-dex/) 纯 Go；**OS / 底层线** 才是 **asm + C**。嵌入式支线见 [18–23 模块](../../../)（ARM64 / U-Boot / 驱动 — 同样是 **启动汇编 + C 内核/驱动** 的分工）。

---

### 什么时候必须写 `.asm`，什么时候只写 `.c`？

| 场景 | 用 |
|------|-----|
| 循环、画图、内存管理算法 | **`.c`** |
| **`HLT`、读 CR、切 CPU 模式、精确时序** | **`.asm`** |
| 启动头 512 B、BIOS 中断 | **`.asm`**（[ipl.asm](../code/ipl.asm)） |
| C 能表达且编译器会优化的 | **`.c`** — 别为了炫技堆汇编 |

**HFT 对照：** 热路径 **C++** 写逻辑；极少数 **内联 asm / 独立 `.S`** 做 **内存屏障、RD TSC、CAS** — 同一思想：**高级语言写 99%，汇编只包不可替代的几条指令**。

---

### 自检

- [ ] 说清 **C 为什么不能直接写 `HLT` / 切模式**  
- [ ] 说清 **`asmfunc.asm` 包装、`bootpack.c` 调用、链接器合并**  
- [ ] 区分 **`ipl.asm` / `nasmhead.asm` / `asmfunc.asm` / `bootpack.c`** 各在哪一层  
- [ ] 能口述 **16→32 例子里 asm 做什么、C 做什么、`call` 如何交接**（见上文完整例子）  
- [ ] 看过 [code/example/](../code/example/) 对照文件

---

← [§3.3 32 位与 C](./section-3.3-32-位模式前期准备与导入-C-语言.md) · [Day 3 README](../README.md) · 下一日 [Day 4](../../day-04-c-graphics/)
