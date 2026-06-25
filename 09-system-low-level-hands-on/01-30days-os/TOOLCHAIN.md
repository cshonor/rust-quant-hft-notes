# 工具链选型 · NASM + GCC + Make

> **本仓库立场：** 全程用 **原版 NASM**，不用原书作者魔改的 **nask**；C 侧用 **GCC**（替代 tolset 里的 **bcc**），构建用 **GNU Make + QEMU**。

---

## 一句话

| | 原书（tolset） | **本仓库** |
|---|----------------|------------|
| 汇编器 | **nask**（作者基于 NASM 风格魔改） | **NASM** |
| C 编译器 | **bcc** | **GCC**（MinGW-w64 / MSYS2） |
| 构建 | 书内 Makefile + 批处理 | **GNU Make** |
| 运行 | QEMU / 软驱 | **QEMU** |

**nask 可以这么理解：** 川合秀实为了方便读者，在 NASM 语法风格上做了定制汇编器；功能上仍是「把 `.nas`/`.asm` 编成机器码」。**我们不必纠结作者的魔改工具** — 直接用业界标准的 **NASM** 即可。

---

## 为什么选 NASM

1. **同一套工具走完全程** — 引导扇区（Day 1–2）→ IPL / bootpack 汇编桩（Day 3+）→ 与 C 链接 → 保护模式切换代码，全用 NASM。
2. **和 GCC、Makefile 自然配合** — `nasm -f bin` 出 `.bin`，`gcc -c` 出 `.o`，`ld` 或书内脚本拼成映像；与 Linux 内核、Bootloader、HFT 底层工程的惯用链一致。
3. **技能可迁移** — 后续读 LKD、写 Linux 模块、改 GRUB/UEFI 相关汇编，文档和示例几乎都是 **NASM/GAS** 生态；不必为一套只在本书出现的工具另学一遍。
4. **输出可对照** — Day 1 手工 HxD 敲的 hex 与 `nasm -l helloos.lst` 列表文件逐字节核对（见 [day-01 section 1.3](./day-01-boot-asm/notes/section-1.3-初次体验汇编程序.md)）。

---

## 和原书 tolset 的关系

| 做法 | 说明 |
|------|------|
| **推荐** | 安装 NASM + GCC + Make + QEMU（见 [SETUP.md](./SETUP.md)） |
| **可选** | 保留 tolset 仅作 **对照**（看作者原始 Makefile、`.nas` 命名） |
| **不必** | 为跟书而必须用 `nask.exe` / `bcc32.exe` |

从原书 `.nas` 移植到 NASM 时，多数指令 **逐行相同**；偶见 nask 专用写法需在 `.lst` 或报错提示下微调（笔记各 Day 会标注）。

---

## 常用命令（示意）

### 汇编引导扇区 / IPL

```bash
# -f bin：纯二进制（无 ELF），适合 512 B 引导扇区
# -l：生成列表文件（偏移 + 机器码 + 源码），对照 HxD
nasm -f bin helloos.asm -o ipl.bin -l helloos.lst
```

### 与 C 协作（Day 3 起）

```bash
nasm -f bin bootpack.asm -o bootpack.bin
gcc -c bootpack.c -o bootpack.o
# 链接布局依当日 Makefile（IPL 读入 bootpack 等）
```

### Makefile 目标链

```makefile
ipl.bin: helloos.asm
	nasm -f bin $< -o $@ -l helloos.lst

helloos.img: ipl.bin
	# 把 ipl.bin 写入 1.44MB 映像偏移 0 …

run: helloos.img
	qemu-system-i386 -fda helloos.img -boot a
```

完整环境步骤见 **[SETUP.md](./SETUP.md)**。

---

## 文件命名约定（本仓库）

| 原书 | 本仓库建议 |
|------|------------|
| `helloos.nas` | `helloos.asm`（或保留 `.nas` 但用 NASM 编译） |
| `naskfunc.nas` | `asmfunc.asm` / `naskfunc.asm` |
| `helloos.lst` | `nasm -l` 生成的列表，格式与 section 1.3 描述一致 |

---

## 相关

- [SETUP.md](./SETUP.md) — Day 0 安装 NASM / GCC / QEMU
- [LEARNING_PLAN.md](./LEARNING_PLAN.md) — 三阶段学习路径
- [day-01 section 1.3](./day-01-boot-asm/notes/section-1.3-初次体验汇编程序.md) — 汇编 ↔ 机器码
- [day-02 section 2.4](./day-02-asm-makefile/notes/section-2.4-Makefile-入门.md) — Makefile 与 NASM 规则
