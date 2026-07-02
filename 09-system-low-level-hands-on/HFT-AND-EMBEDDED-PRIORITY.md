# HFT / 嵌入式主线 · 学什么、先搁置什么

> 与 [LEARNING-CHAIN](../../LEARNING-CHAIN.md)（`08 TLPI → 09 自制 OS → … → 15 HFT`）对齐。  
> **结论先说：** 现阶段 **C 和 CSAPP 64 位** 是主菜；**16 位实模式汇编** 在 haribote 里 **浅看带过**，不必死磕 GDT/CR0 细节。

---

## 一、现阶段核心：优先吃透 C

| 理由 | 说明 |
|------|------|
| **工业栈都以 C 为根** | Linux 内核、DPDK、低延迟网络、嵌入式 Linux 驱动 — 主体都是 C |
| **回看 OS 无门槛** | C 熟练后，进程、内存、调度、syscall 只是「多了一层内核 API」 |
| **HFT 离不开 C 底子** | 底层优化、FFI、与内核/网卡交互、读 CSAPP 反汇编 — 都建立在 C + 内存模型上 |

**在本仓库里对应：**

- **主投入：** [01-CSAPP-3rd](../../01-CSAPP-3rd/) · [08-The-Linux-Programming-Interface](../../08-The-Linux-Programming-Interface/) · [05-Linux-Kernel-Development](../../05-Linux-Kernel-Development/)
- **haribote 里 C 从哪进：** [Day 3 `HariMain`](./01-30days-os/day-03-32bit-c/) → [Day 4 显存/指针](./01-30days-os/day-04-c-graphics/) — **重点看 `bootpack.c` 怎么写逻辑**，不是背每行 16 位汇编

---

## 二、16 位实模式汇编：暂时搁置深挖

你现在写的 **512 B 引导扇区、IPL、`INT 0x13`**，属于 **完整自制 OS / 手写 BIOS Bootloader** 才常用到的技能。

| 场景 | 要不要深钻 16 位 |
|------|------------------|
| **HFT（x86 Linux 服务器）** | **几乎不用** — 用户态 C++，偶发内联 asm |
| **ARM 嵌入式 Linux** | **不用** — 上电走 U-Boot / ATF，不是 x86 实模式 |
| **haribote 启蒙** | **浅看** — 知道「能 boot、能读盘、能切到 32 位跑 C」即可 |

**只需记住的宏观结论（不必现在推公式）：**

```text
CPU 上电 → 默认 16 位实模式
         → BIOS / IPL 做最少的事（读盘、切 VGA…）
         → 切到 32 位保护模式（GDT、CR0…）→ 现代 C 内核跑起来
```

GDT 每一项、CR0 每一位、CHS 寻址公式 — **第二遍或对照 LKD 时再抠**；第一遍 **跑通 QEMU + 看懂故事线** 就够。

**haribote 各天「浅看」清单：**

| Day | 带走什么 | 不必死磕 |
|-----|----------|----------|
| 1–2 | 512 B、`55 AA`、`0x7C00`、Makefile | 每条 `MOV` 与 BIOS 寄存器 |
| 3 | IPL 读 bootpack、`HariMain`、四文件分工 | `INT 0x13` 重试循环、A20 键盘控制器 |
| 4 | **指针写 VRAM**、调色板概念 | CLI/PUSHFD 每条指令 |
| 5+ | 中断、GDT/IDT **概念** | 与 Linux `idt_table` 对照即可，不必默写汇编 |

详读：[Day 3 README · 软盘布局](./01-30days-os/day-03-32bit-c/README.md) · [OUTLINE 🔴/🟡/⚪](./01-30days-os/OUTLINE.md)

---

## 三、汇编只学两类（对你有用）

| 类型 | 何时学 | 用途 |
|------|--------|------|
| **x86-64 汇编（CSAPP）** | **紧接 C 之后** | 看懂 C++/Rust 编译结果；缓存、流水线、延迟毛刺 — **HFT 刚需** |
| **ARM64 汇编** | **嵌入式飞控阶段再学** | 设备树、U-Boot、驱动里少量 asm — 与当前 haribote **并行优先级低** |

**不要混为一谈：**

| | haribote 16 位 | CSAPP x86-64 | ARM64 |
|--|----------------|--------------|-------|
| 位宽 | 16 | 64 | 64 |
| 典型场景 | 软盘 IPL | HFT 反汇编、perf | 嵌入式 Linux |
| 你现在 | 浅看 | **主攻** | 延后 |

---

## 四、推荐学习顺序（叠加在仓库链路上）

```text
1. C 语言扎实
   语法、指针、内存、结构体、系统调用
   ↔ 08 TLPI · haribote Day 3–4 的 bootpack.c

2. CSAPP：x86-64 汇编 + 缓存 + 内存层次
   ↔ 01-CSAPP Ch3 / Ch5 / Ch6

3. Linux 系统编程 + 内核基础
   ↔ 08 TLPI 全书 · 05 LKD 选读

4. 09 自制 OS（haribote / MikanOS）
   第一遍：跑通 + 概念图；16 位代码浅看
   第二遍（可选）：与 LKD 中断/页表/调度对照

5. 10–14 网络 · 15 HFT
   绑核、热路径、少 syscall、DPDK 生态

6. 嵌入式 Linux（另线）
   ARM64 asm、设备树 — 与 HFT 可并行但非当前重点

7. 有空再回头
   32 位保护模式切换、16 位 IPL 细节 — 当读内核 boot 或写 Bootloader 时
```

与 [LEARNING-CHAIN](../../LEARNING-CHAIN.md) 一致：**08 不必等 haribote 做完**；C + CSAPP 可与 **Day 3–4 并行**。

---

## 五、和「30 天自制 OS」怎么配合（不纠结）

| 你的担心 | 实际建议 |
|----------|----------|
| 16 位汇编要不要精通 | **不要** — 能读懂 [ipl.asm](./01-30days-os/day-03-32bit-c/code/sec-3.1-ipl-int13-disk-load/ipl.asm) 在干什么即可 |
| Day 3 读盘、模式切换好难 | 用 [Day 3 README 直白版](./01-30days-os/day-03-32bit-c/README.md) 建立图景；**细节跳过不丢人** |
| Day 4 指针 / VRAM | **值得多练** — 和 mmap、共享内存、行情缓冲 **同一套思维** |
| 30 天要不要全做完 | 按 [OUTLINE](./01-30days-os/OUTLINE.md) **🔴 必做、⚪ 可跳**；GUI 窗口类对 HFT **可大幅压缩** |
| MikanOS（02） | UEFI/64 位 — **更接近现代**；时间紧可 **01 启蒙后直跳 02 部分章节** |

---

## 六、一句话

**主菜：C + CSAPP 64 位 + Linux 系统编程 → HFT。**  
**haribote 16 位：开胃菜 — 知道开机链和「汇编搭台、C 唱戏」，别在实模式里安家。**

---

## 相关

| 文档 | 用途 |
|------|------|
| [01-30days-os/LEARNING_PLAN.md](./01-30days-os/LEARNING_PLAN.md) | 原书 30 天节奏 |
| [01-30days-os/OUTLINE.md](./01-30days-os/OUTLINE.md) | 每日 🔴/🟡/⚪ 裁剪 |
| [§3.3.6 引入 C 与 HFT](./01-30days-os/day-03-32bit-c/notes/section-3.3.6-引入C与嵌入式HFT.md) | 四文件分工短注 |
