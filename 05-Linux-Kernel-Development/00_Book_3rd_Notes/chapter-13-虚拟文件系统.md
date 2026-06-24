# Ch 13 · 虚拟文件系统 · The Virtual Filesystem

> **Linux Kernel Development 3rd** · Robert Love · **背景**  
> 本章定位：**VFS 抽象层** — 四大对象、`file_operations`、**dcache**、挂载与进程 fd 表。统一 **open/read/write** 如何落到 ext4/FAT/管道/设备。

---

## 本节结构

| 节 | 主题 | 带走什么 |
|----|------|----------|
| **① 抽象接口** | VFS 粘合剂 | syscall ↔ 具体 FS |
| **② 四大对象** | superblock/inode/dentry/file | 面向对象 C |
| **③ 操作表** | `*_operations` | 函数指针多态 |
| **④ dcache** | 目录项缓存 | 路径解析加速 |
| **⑤ FS 数据结构** | `file_system_type` · `vfsmount` | 注册与挂载 |
| **⑥ 进程相关** | `files_struct` 等 | fd · 命名空间 |

---

### ① 通用文件系统接口与抽象层

**VFS** = 用户 **系统调用**（`open`/`read`/`write`/`close`…）与 **底层存储/实现** 之间的 **粘合剂**。

```
用户态 read(fd, buf, n)
    ▼
sys_read() ──► VFS（统一语义）
    ▼
具体 FS：ext4 / xfs / fat / proc / sysfs / socket…
    ▼
块设备 / 内存 / 网络 / 驱动…
```

| 设计 | 效果 |
|------|------|
| **抽象层**规定统一概念与数据结构 | 各 FS **隐藏细节** |
| 对内核其余部分 | **所有文件系统看起来一样** |

| 可共存示例 | NTFS · FAT · ext4 · 各类 Unix FS… |

→ [Ch 1](./chapter-01-Linux内核简介.md) **一切皆文件** · [Ch 5](./chapter-05-系统调用.md) · [07-TLPI Ch3 文件 I/O](../../07-The-Linux-Programming-Interface/chapter-03-file-io/)

**HFT：** 热路径 **`read`/`write`/`mmap`/`send`** 都经 VFS 或并行子系统；排障可分层：**syscall → VFS → 具体 FS/协议栈**。

→ [02 SysPerf Ch8 VFS 追踪](../../02-Systems-Performance-2nd/chapter-08-file-systems/notes/section-8.4-文件系统架构与特性.md)

---

### ② VFS 的面向对象设计 · 四大对象

内核用 **纯 C**，VFS 用 **对象 + 操作表** 模拟 OOP：

| 对象 | 代表 | 主要内容 |
|------|------|----------|
| **超级块 superblock** | 一个 **已挂载** 的文件系统实例 | FS 级控制信息（块大小、魔数、挂载状态…） |
| **索引节点 inode** | 一个 **具体文件**（含目录） | **元数据**：权限、大小、所有者、时间戳… **不含文件名** |
| **目录项 dentry** | 路径中的 **一段名字**（目录或文件名） | 路径解析组件；**目录也是文件** |
| **文件 file** | 进程 **已打开** 的文件 | **进程视角**：打开模式、**f_pos 偏移**、标志… |

#### 关系简图

```
挂载点 /dev/sda1
    └── superblock (ext4 实例)
            └── inode (文件元数据)
                    ▲
            dentry ("foo.c" 这一节名字) ──► 路径链 /home/.../foo.c
                    ▲
            file (某进程 fd=3 打开它) ──► 当前读写偏移
```

| 区分 | |
|------|--|
| **inode** | 「这个文件是什么」— 全局 FS 内一份 |
| **file** | 「这个进程怎么用它」— 每打开一次一份 |

→ **Ch 16** 页缓存挂在 address_space / inode 侧

---

### ③ 操作对象 · Operations Objects

每个主对象内嵌 **函数指针表** — 具体 FS **实现方法**：

| 操作结构 | 父对象 | 典型方法 |
|----------|--------|----------|
| **`super_operations`** | superblock | 读写 superblock、同步 FS |
| **`inode_operations`** | inode | `lookup`、`create`、`mkdir`… |
| **`dentry_operations`** | dentry | `d_hash`、`d_compare`… |
| **`file_operations`** | file | **`read`、`write`、`mmap`、`ioctl`**… |

```c
/* 概念：驱动/FS 填充 file_operations */
struct file_operations {
    ssize_t (*read)(struct file *, char __user *, size_t, loff_t *);
    ssize_t (*write)(struct file *, const char __user *, size_t, loff_t *);
    /* ... */
};
```

| 多态 | VFS 调用 `file->f_op->read(...)` — 实际跑到 ext4 或 pipe 或设备驱动 |

→ [Ch 5](./chapter-05-系统调用.md) 替代 syscall：**字符设备** 也靠 **`file_operations`**

→ 教学对照：[08-1 Day 18–19 FAT](../../08-system-low-level-hands-on/08-1-30days-os/notes/day-18-FAT与目录项.md)（具体 FS 在 VFS 之下）

---

### ④ 目录项缓存 · Dentry Cache · dcache

**路径解析**（`/home/dracula/src/the_sun_sucks.c`）— 字符串遍历 + 查找，**昂贵**。

**dcache** 缓存已解析的 **dentry** → 同路径再次访问 **更快**。

#### dentry 三种状态

| 状态 | 含义 |
|------|------|
| **使用中** | VFS **正在用** |
| **未使用** | 暂不用，但 **留在缓存** 备查 |
| **负缓存（negative）** | 路径 **无效/不存在** — 缓存「没有这文件」→ **快速拒绝** 后续无效 open |

```
第一次 open 不存在文件 ──► 负 dentry 入缓存
第二次同路径 open     ──► 不必再深入 FS 查找
```

| 观测 | `sar -v` dentry/inode cache — [SysPerf §8.6](../../02-Systems-Performance-2nd/chapter-08-file-systems/notes/section-8.6-观测工具.md) |

**HFT：** 日志/配置 **冷路径** 才关心 dcache；热路径 **已打开 fd** 或 **`mmap`** 绕过反复路径解析。

---

### ⑤ 与文件系统相关的数据结构

| 结构 | 作用 |
|------|------|
| **`file_system_type`** | 描述一种 FS **类型**（如 ext4）— 能力、注册、`mount` 入口 |
| **`vfsmount`** | 一次 **具体挂载实例** — 挂载点、设备名、**挂载标志** |

```
file_system_type "ext4"  ──注册──► 内核 FS 列表
        │
        mount /data
        ▼
   vfsmount（/data 上的 ext4 实例）──► superblock
```

---

### ⑥ 与进程相关的数据结构

每进程与 VFS 通过三类结构关联：

| 结构 | 内容 |
|------|------|
| **`files_struct`** | **打开文件表** · **fd 数组** → `struct file *` |
| **`fs_struct`** | **当前工作目录 pwd** · **根目录 root** |
| **`namespace`（挂载命名空间）** | 进程看到的 **挂载树视图** |

#### 命名空间

| 默认 | 所有进程 **共享** 同一挂载命名空间 |
|------|----------------------------------|
| 容器 | 每进程可有 **独立** 挂载层次（Docker 等） |

```
进程 A: files_struct ── fd[0,1,2, socket_fd, log_fd ...]
        fs_struct    ── pwd=/opt/strategy  root=/
        namespace    ── 看到的主机挂载树
```

→ **Ch 3** 进程资源「打开的文件」· **Ch 12** inode Slab 缓存

---

### 从 open 到 read（概念路径）

```
open("/path/file", O_RDONLY)
    ▼
路径 walk ──► dcache 命中？ ──► inode lookup
    ▼
分配 struct file ──► 填入 files_struct->fd[]
    ▼
read(fd, ...)
    ▼
VFS sys_read ──► file->f_op->read ──► ext4_file_read / …
    ▼
（可能）页缓存 Ch 16 ──► 块层 Ch 14
```

---

### Ch 13 小结

| 对象 | 一句话 |
|------|--------|
| **superblock** | 已挂载 FS 实例 |
| **inode** | 文件元数据 |
| **dentry** | 路径名组件 + **dcache** |
| **file** | 进程打开实例 + 偏移 |
| **`*_operations`** | 具体 FS/驱动实现 |
| **`files_struct`** | **fd 表** |

---

### 检查单

- [ ] 画出 **inode vs dentry vs file** 分工
- [ ] 说出 **`file_operations`** 在 VFS 多态中的作用
- [ ] 解释 **dcache 负缓存** 用途
- [ ] 区分 **`file_system_type`** 与 **`vfsmount`**
- [ ] 知 **`files_struct` / `fs_struct` / namespace** 各管什么
- [ ] HFT：热路径 **长生命 fd + mmap** vs 冷路径反复 `open`

---

## 相关章节

- 上一章：[chapter-12-内存管理.md](./chapter-12-内存管理.md)
- 下一章：[chapter-14-块IO层.md](./chapter-14-块IO层.md)
- 本模块导读：[README.md](./README.md) · [OUTLINE.md](./OUTLINE.md)
