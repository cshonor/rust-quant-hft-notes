# Ch 2 · 内核入门 · Getting Started with the Kernel

> **Linux Kernel Development 3rd** · Robert Love · **实操入门**  
> 本章定位：**拿源码 → 认目录 → 配置编译安装**；并牢记 **内核开发 ≠ 用户态 C** 的硬性约束。

---

## 本节结构

| 节 | 主题 | 带走什么 |
|----|------|----------|
| **① 获取源码** | Git / tarball / patch | 别解压到 `/usr/src/linux` |
| **② 源码树** | `arch` `drivers` `fs`… | 按子系统找代码 |
| **③ 编译安装** | config → make → install | `menuconfig` · `make -j` · modules |
| **④ 开发差异** | Beast of a Different Nature | **无 libc · 小栈 · 同步 · 无 FP** |

---

### ① 获取内核源码 · Obtaining the Kernel Source

#### Git（推荐）

内核社区 **强烈推荐 Git** 管理源码树：

```bash
git clone https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git
cd linux
git pull    # 跟进主线更新
```

| 方式 | 优点 |
|------|------|
| **Git** | 易更新 · 易打补丁 · 易切分支/tag · 与社区工作流一致 |

#### 压缩包

也可从 [kernel.org](https://www.kernel.org/) 下载 **bzip2 / gzip** 源码包并解压。

| 建议 | 原因 |
|------|------|
| **放在 `~/` 等用户目录** | 开发不必 root |
| **不要解压到 `/usr/src/linux`** | 避免污染系统树、误链系统头文件 |

#### 使用补丁 · Patches

社区交流以 **patch** 为通用语言：

```bash
cd linux
patch -p1 < ../patch-x.y.z
```

`-p1` 剥掉补丁路径前缀一层，与 `git am` / `git apply` 同属日常工具链。

→ 收官：[chapter-20-补丁开发和社区.md](./chapter-20-补丁开发和社区.md)

---

### ② 内核源码树 · The Kernel Source Tree

按 **功能子系统** 划分的顶层目录（常逛）：

| 目录 | 内容 |
|------|------|
| **`arch/`** | **架构相关** — x86、arm64、引导、平台代码 |
| **`drivers/`** | **设备驱动** — 网卡、块设备、GPU… |
| **`fs/`** | **VFS** 与各文件系统实现 |
| **`include/`** | **内核头文件** — 对外/对内 API |
| **`kernel/`** | **核心子系统** — 调度、信号、锁… |
| **`mm/`** | **内存管理** — 页、slab、VMA… |
| **`net/`** | 网络协议栈 |
| **`ipc/`** | 进程间通信 |
| **`lib/`** | 内核自用库函数 |
| **`init/`** | 启动与 `main` 路径 |

**读代码习惯：** 先 **`include/linux/`** 找类型/宏 → 再进 **`kernel/` `mm/` `fs/`** 对应章节的实现。

→ 本书映射：**Ch 3–4** `kernel/` · **Ch 12** `mm/` · **Ch 13** `fs/` · **Ch 7–8** `arch/*/kernel/` 中断路径

---

### ③ 编译和安装内核 · Building and Installing the Kernel

#### 配置

编译前 **必须配置**（生成 `.config`）：

| 命令 | 界面 |
|------|------|
| `make config` | 命令行逐项问答 |
| `make menuconfig` | **ncurses** 图形菜单（最常用） |
| `make defconfig` | 当前架构 **默认配置** 起点 |

还可 `make oldconfig` 在升级版本时合并新旧选项。

#### 编译

```bash
make -j$(nproc)    # 或 make -j8；通常 核心数 ~ 2× 核心
```

| 产物 | 说明 |
|------|------|
| **`vmlinuz` / `bzImage` 等** | 引导用内核镜像（因架构/引导器而异） |
| **`*.ko`** | 可加载 **内核模块** |

#### 安装

| 步骤 | 命令 / 位置 |
|------|-------------|
| **内核镜像** | 依 **架构 + GRUB/systemd-boot** 手动拷贝并改引导项 |
| **模块** | `make modules_install` → **`/lib/modules/<version>/`** |

**HFT 对照：** 调 **网卡驱动、PREEMPT、HZ、隔离 CPU** 往往从 **自建内核 + `menuconfig`** 开始；生产环境务必保留可回滚的已知-good 内核条目。

→ 课程前置：[01 LFS](../../05-Linux-Kernel-Development/01_Course_LFS/) · [02 内核编程 7 讲](../../05-Linux-Kernel-Development/02_Course_Kernel_7Lectures/)

---

### ④ 内核开发的特点 · A Beast of a Different Nature

内核与用户态程序 **不是同一种 C 环境**。下列规则 **违反即 oops / 死锁 / 栈炸**。

#### 无标准 C 库

| 用户态 | 内核态 |
|--------|--------|
| `printf` | **`printk`**（带 **日志级别**） |
| `malloc` | **`kmalloc` / `vmalloc` / slab**（Ch 12） |
| `string.h` 全套 | 内核 **`lib/`** 自实现子集 |
| 链接 glibc | **不能** 链接标准 C 库 |

#### GNU C 扩展

内核 **非严格 ANSI C**，大量使用 **GCC 扩展**：

| 扩展 | 用途 |
|------|------|
| **`inline` 函数** | 热路径零开销抽象 |
| **内联汇编** | 直接操作寄存器、屏障、原子 |
| **`likely()` / `unlikely()`** | **分支预测** 提示 — 优化常见/罕见路径 |

```c
if (likely(ptr != NULL)) {
    /* 常见路径 */
}
```

#### 无内存保护

| 现象 | 后果 |
|------|------|
| 非法访问 | 无 **SIGSEGV** — 往往 **oops / panic** |
| 内核内存 | **不可换页** — 每占 1 字节 = **真实物理内存 −1** |
| 泄漏 | 重启前 **不会** 还给系统 |

#### 禁止浮点（通常）

用户态由内核 **惰性保存/恢复 FP 寄存器**；内核路径 **默认不处理 FP 状态** → **一般禁止浮点运算**（特殊代码需显式 `kernel_fpu_begin/end` 等）。

#### 小而固定的栈

| 事实 | 开发约束 |
|------|----------|
| 内核栈常 **4KB 或 8KB** | **禁止** 栈上大数组/大结构体 |
| 每进程独立内核栈 | 深度递归、大 `alloca` → **栈溢出** |

→ 对照用户态：[01-CSAPP](../../01-CSAPP-3rd/) 栈与调用约定 · [08-1 Day 1 汇编栈帧](../../08-system-low-level-hands-on/08-1-30days-os/notes/day-01-从计算机结构到汇编入门.md)

#### 同步与并发

并发来源多：**抢占**、**SMP**、**硬/软中断**、**内核线程** → 极易 **竞态**。

| 机制 | 场景（详见 Ch 9–10） |
|------|----------------------|
| **自旋锁** | 短临界区、不可睡眠 |
| **信号量 / mutex** | 可睡眠、较长临界区 |
| **RCU** | 读多写少 |

**HFT：** 用户态网关用 **无锁队列 + 绑核**；内核里对应的是 **关中断、per-CPU、原子、锁顺序** — 错一层就是 **微秒级抖动或整机卡死**。

#### 可移植性

Linux **高度可移植** — 代码应：

| 原则 | 反例 |
|------|------|
| **字节序中立** | 假设 little-endian |
| **64 位兼容** | 假设 `int` = 指针宽度 |
| **不硬编码页大小** | 写死 4096 而不 `PAGE_SIZE` |
| **`arch/` 隔离** | 在通用代码里写 x86 汇编 |

---

### Ch 2 小结

| 问题 | 答案 |
|------|------|
| 怎么拿源码？ | **`git clone` + `pull`** 优先；tarball 放用户目录 |
| 怎么打补丁？ | **`patch -p1 <`** 或 git 系列 |
| 关键目录？ | **`arch` `drivers` `fs` `kernel` `mm` `include`** |
| 怎么编？ | **`menuconfig` → `make -jN` → 装镜像 + `modules_install`** |
| 和用户态最大不同？ | **无 libc · printk · 小栈 · 无换页 · 严同步 · 慎 FP** |

---

### 检查单

- [ ] 能在 **个人目录** 完成 clone、`menuconfig`、`make -j`
- [ ] 说清 **`printk` vs `printf`**、**内核栈大小** 约束
- [ ] 知道 **`likely/unlikely`** 是分支预测而非逻辑改变
- [ ] 能指出 **`kernel/`、`mm/`、`fs/`** 各对应本书哪几章
- [ ] 理解为何 HFT 调内核参数时要 **可回滚引导项**

---

## 相关章节

- 上一章：[chapter-01-Linux内核简介.md](./chapter-01-Linux内核简介.md)
- 下一章：[chapter-03-进程管理.md](./chapter-03-进程管理.md)
- 本模块导读：[README.md](./README.md) · [OUTLINE.md](./OUTLINE.md)
