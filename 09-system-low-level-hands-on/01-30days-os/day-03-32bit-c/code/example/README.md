# 教学示例 · 汇编 + C 怎么配合（§3.4）

**不是完整可启动软盘** — 演示 **nasmhead 切 32 位 + call C**。笔记：[§3.4.3](../notes/section-3.4.3-16切32与call-C完整例子.md) · [§3.4 导读](../notes/section-3.4-汇编与-C-的结合.md)

| 文件 | 作用 |
|------|------|
| [nasmhead-minimal.asm](./nasmhead-minimal.asm) | **汇编搭台**：CLI、LGDT、CR0.PE、设段/栈、`call kernel_main` |
| [kernel_main.c](./kernel_main.c) | **C 唱戏**：循环写 VGA 文本 `"Hello 32-bit C!"` |

原书对应：`nasmhead.asm` + `bootpack.c` 的 **`HariMain`**。

---

## 配合关系（一句话）

**汇编** 做完 C 做不了的模式切换 → **`call kernel_main`** → **C** 写字符串循环等业务逻辑。

---

## 链接（Linux / WSL / MSYS2 示意）

需 **gcc 32 位**、**nasm**、**ld**：

```bash
cd day-03-32bit-c/code/example
nasm -f elf32 nasmhead-minimal.asm -o nasmhead.o
gcc -m32 -c kernel_main.c -o kernel_main.o -ffreestanding -nostdlib -fno-pie
ld -m elf_i386 -o bootpack.elf nasmhead.o kernel_main.o
```

> 真正 haribote 还要和 **IPL 读盘地址、软盘布局、nasmhead 链接地址** 对齐 — 见原书 Makefile；本目录 **只教 asm/C 分工**。

---

## 与 haribote 文件对照

| 本示例 | 原书 |
|--------|------|
| `nasmhead-minimal.asm` | `nasmhead.asm`（+ 开 A20、BIOS 切 VGA 等） |
| `kernel_main()` | **`HariMain()`** |
| （未含） | `asmfunc.asm` → **`io_hlt()`** 等 C 调用的汇编补丁 |
| （未含） | [ipl.asm](../ipl.asm) — 16 位读 bootpack |
