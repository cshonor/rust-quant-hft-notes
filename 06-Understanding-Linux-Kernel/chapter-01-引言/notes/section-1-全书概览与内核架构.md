## 1. 全书概览与内核架构

> **来源：** *Understanding the Linux Kernel* 3rd（ULK）· Bovet & Cesati · **Linux 2.6**

---

### 一、本书定位

ULK 从**源代码级**解析 Linux 内核：不讲「怎么用内核 API」，而讲**内核内部如何实现**——数据结构、算法、关键路径。在本仓库 Linux 链上：

```
05 LKD   … 子系统做什么（功能地图）
06 ULK   … 代码里长什么样（本书记）  ← 你在这里
07 Gorman … 虚拟内存专著
08 TLPI  … 用户态 syscall 接口
```

> **版本提醒：** ULK 基于 **2.6**；读时 **概念优先**（进程、页表、中断、调度），结构体名字以本机 `include/linux/*.h` 为准对照 modern kernel。

---

### 二、全书覆盖的核心组件

| 主题 | 大白话 | ULK 章节 |
|------|--------|----------|
| **内存管理** | 物理页怎么分配、虚拟内存怎么映射 | [Ch 2](../chapter-02-内存寻址.md) · [Ch 8](../chapter-08-内存管理.md) · [Ch 9](../chapter-09-进程地址空间.md) · [Ch 17](../chapter-17-页回收.md) |
| **进程调度** | 哪个进程下一个跑 CPU | [Ch 3](../chapter-03-进程.md) · [Ch 7](../chapter-07-进程调度.md) |
| **中断与同步** | 硬件打断、多核下怎么不乱 | [Ch 4](../chapter-04-中断与异常.md) · [Ch 5](../chapter-05-内核同步.md) |
| **虚拟文件系统（VFS）** | 打开/读/写文件的内核路径 | [Ch 12](../chapter-12-VFS.md) · [Ch 16](../chapter-16-文件访问.md) |
| **设备驱动 / I/O** | 内核怎么跟硬件说话 | [Ch 13](../chapter-13-IO架构.md) · [Ch 14](../chapter-14-块设备.md) |
| **系统调用** | 用户程序进内核的入口 | [Ch 10](../chapter-10-系统调用.md) |
| **页缓存** | 读文件为什么有时很快 | [Ch 15](../chapter-15-页缓存.md) |

HFT 热路径精读 → [OUTLINE.md](../OUTLINE.md) 标 🔴 的章；VFS/Ext2 等可 ⚪ 跳过。

---

### 三、关键设计理念

#### 1. 逻辑地址 → 物理地址

- 用户程序和内核大多用**逻辑（虚拟）地址**编程，不直接摸物理 RAM。
- MMU + 页表把虚拟地址**转换**成物理地址，内核才能安全、高效地操作硬件。
- **对应章节：** [Ch 2 内存寻址](../chapter-02-内存寻址.md) → [Ch 8–9 内存管理 / 地址空间](../chapter-08-内存管理.md)

#### 2. 单体内核（Monolithic）+ 模块化

- Linux 是**单体内核**：调度、内存、VFS、驱动都在同一地址空间，调用快。
- **可加载模块（module）** 让驱动等子系统**运行时动态插入**，兼顾灵活与性能。
- **对应章节：** [附录 B 模块](../appendix-B-模块.md)

#### 3. 硬件 ↔ 应用程序的桥梁

```
应用程序（用户态）
    ↓ syscall（Ch 10）
内核（特权态：调度 Ch 7 · 内存 Ch 8–9 · VFS Ch 12 …）
    ↓ 驱动 / 中断（Ch 4 · Ch 13）
硬件（CPU · 内存 · 磁盘 · 网卡）
```

内核职责：**隔离进程、分配资源、抽象硬件**，保证多用户、多任务下稳定高效。

#### 4. SMP 与多用户

- **SMP（对称多处理）：** 多 CPU 核共享内存；调度、锁、中断需专门设计（Ch 5、Ch 7）。
- **多用户：** 每个进程独立地址空间（Ch 9），权限环（用户态 / 内核态）防止互相搞破坏。

#### 5. 与 Unix 变体的差异

ULK 会对比 Linux 与其他 Unix 在实现上的取舍（调度策略、内存模型、VFS 层等）——读时留意「**Linux 特有**」vs「**Unix 通用**」。

---

### 四、与仓库其他模块的交叉

| 模块 | 关系 |
|------|------|
| [05 LKD](../../05-Linux-Kernel-Development/) | 先读「做什么」，再用 ULK 下潜「怎么做」 |
| [07 Gorman](../../07-Linux-Virtual-Memory-Manager/) | ULK Ch 8–9/17 是 MM 总览；Gorman 专精 VM |
| [08 TLPI](../../08-The-Linux-Programming-Interface/) | Ch 10 syscall 的用户态视角 |
| [09 自制 OS](../../09-system-low-level-hands-on/) | 自己写 OS 时对照「Linux 正式版怎么做的」 |

---

### 五、读 ULK 的实用建议

1. **不要死磕 2.6 版本号** — `task_struct`、CFS 等 modern 内核已变，抓**机制**即可。
2. **配合源码** — 本机 kernel 或 [elixir.bootlin.com](https://elixir.bootlin.com/linux/latest/source) 对照读。
3. **按 OUTLINE 🔴 章选读** — HFT 优先：中断、调度、内存、syscall。

---

← [Ch 1 导读](../README.md) · 下一章 [Ch 2 内存寻址](../chapter-02-内存寻址.md)
