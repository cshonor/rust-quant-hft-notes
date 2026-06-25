## ④ Makefile 入门

步骤变多：**NASM 编 `ipl.bin`** → **拼进 1.44 MB 映像** → **QEMU 启动** … 若每一步都手敲一长串命令，或堆一堆 **`.bat`**，目录又乱又容易漏。

**Makefile** 把「目标、依赖、命令」写进 **一个纯文本文件**；终端里只敲 **`make`**，由系统里的 **make 工具** 按规则自动执行（只重做改过的步骤）。

---

### 不用专门软件 — VS Code 就能写

| 要点 | 说明 |
|------|------|
| **格式** | **纯文本**，没有特殊二进制格式 |
| **文件名** | 必须叫 **`Makefile`**（**M 大写**，无 `.txt` 后缀） |
| **编辑器** | **VS Code** / Cursor / 记事本均可 — 与写 `helloos.nas` 一样 **新建 → 保存** |
| **常见坑** | 若存成 `Makefile.txt`，`make` **找不到**；配方行必须用 **Tab 缩进**，不能全用空格 |

在 VS Code 中：

1. 工程目录（与 `helloos.nas` 同级）→ **新建文件** → 保存为 **`Makefile`**
2. 写入下面的规则
3. **终端**（VS Code `` Ctrl+` ``）→ `cd` 到该目录 → 输入 **`make`**

> **make 本身** 是已安装的工具（[SETUP §3.5](../../SETUP.md#35-确认-make)：`make --version`）。**Makefile** 只是告诉 make「要做什么」的说明书。

---

### 三条规则在干什么

```makefile
# 目标: 依赖
# 	命令（行首必须是 Tab）

ipl.bin: helloos.nas
	nasm -f bin $< -o $@ -l helloos.lst

helloos.img: ipl.bin
	dd if=/dev/zero of=$@ bs=512 count=2880
	dd if=ipl.bin of=$@ conv=notrunc

run: helloos.img
	qemu-system-i386 -fda helloos.img -boot a
```

| 目标 | 依赖 | 做什么 |
|------|------|--------|
| **`ipl.bin`** | `helloos.nas` | **NASM** 汇编 → **512 B** 引导扇区（见 [Day 1 §1.4](../day-01-boot-asm/notes/section-1.4-加工润色.md)） |
| **`helloos.img`** | `ipl.bin` | 生成 **1,474,560 B** 软盘，把 `ipl.bin` **写到偏移 0** |
| **`run`** | `helloos.img` | 调 **QEMU** 启动 |

**Make 变量简写（知道即可）：**

| 符号 | 含义 |
|------|------|
| **`$<`** | 本条规则的第一个依赖（如 `helloos.nas`） |
| **`$@`** | 本条规则的目标（如 `ipl.bin`） |

原书：`nask helloos.nas helloos.lst ipl.bin` → 本仓库：**`nasm -f bin helloos.nas -o ipl.bin -l helloos.lst`**（`.nas` 后缀不用改）。

---

### 拼 1.44 MB 映像：和 Day 1 的关系

- **`nasm` 只产出 512 B 的 `ipl.bin`**（引导扇区）。
- **昨天 HxD** 是直接编辑 **整盘 1.44 MB**；**今天** 可以：
  - **Makefile 里用 `dd`**（**MSYS2 / Git Bash** 终端里 `make` — `dd` 在这类环境可用），或
  - 用 HxD 打开模板 [helloos.img](../day-01-boot-asm/code/helloos.img)，把 `ipl.bin` **覆盖到文件开头**（与 [1.4 做法 A](../day-01-boot-asm/notes/section-1.4-加工润色.md) 相同）

`dd` 两行含义：

```text
dd if=/dev/zero of=helloos.img bs=512 count=2880   # 2880×512 = 1,474,560 B 全零底稿
dd if=ipl.bin of=helloos.img conv=notrunc          # 只覆盖开头 512B，不截断文件
```

---

### 怎么用

在 **含 `Makefile` 的目录** 打开终端：

```bash
make              # 默认构建第一个目标，或构建 helloos.img 的依赖链
make helloos.img  # 只构建映像（ipl.bin 已最新则跳过 nasm）
make run          # 构建后启动 QEMU（需写好 run 目标）
make clean        # 若定义了 clean，删除中间文件
```

**增量构建：** 只改注释、没动 `helloos.nas` 时，再敲 `make` 可能 **跳过 nasm**（因为 `ipl.bin` 比 `.nas` 新）— 这就是 Makefile 相对手敲命令的好处。

---

### 和 `.bat`、手敲命令对比

| | 手敲 / `.bat` 堆叠 | **`Makefile` + `make`** |
|---|-------------------|-------------------------|
| 命令长度 | 每次复制一长串 | 平时只打 **`make`** |
| 依赖顺序 | 自己记、易漏拼盘 | **目标–依赖** 自动排序 |
| 改了一处 | 可能全量重跑 | **只重建过期的目标** |
| 文件 | 多个脚本 | **一个 `Makefile`** |
| 行业习惯 | Windows 批处理 | **Linux 内核 / HFT** 与 CMake/Ninja 同族思想 |

**HFT：** 策略、网关工程里 **CMake / Make / Ninja** — 同一套路：**声明依赖，工具链执行**。

---

### 自检

- [ ] 工程根目录有 **`Makefile`**（不是 `makefile.txt`）
- [ ] 配方行用 **Tab** 缩进
- [ ] `make` 能生成 **`ipl.bin`（512 B）**
- [ ] `make` 能生成 **`helloos.img`（1,474,560 B）**，QEMU 仍出 **`hello, world`**
- [ ] 说清：**Makefile 是文本**；**make 是读它的程序**

---

← [2.3 先制作启动区](./section-2.3-先制作启动区.md) · 下一日 [Day 3](../../day-03-32bit-c/)
