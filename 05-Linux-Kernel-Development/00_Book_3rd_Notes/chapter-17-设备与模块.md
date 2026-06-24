# Ch 17 · 设备与模块 · Devices and Modules

> **Linux Kernel Development 3rd** · Robert Love · **背景**  
> 本章定位：**块/字符/网络设备** 分类、**统一设备模型**（kobject/kset/kref）、**sysfs**、**uevent**、**内核模块**。读驱动、`/sys` 调参、热插拔与 **Ch 5「用 sysfs 替代新 syscall」** 的落地页。

---

## 本节结构

| 节 | 主题 | 带走什么 |
|----|------|----------|
| **① 设备类型** | block/char/net/misc | socket 例外 |
| **② 统一设备模型** | kobject 族 | 拓扑 · 电源管理 |
| **③ sysfs** | `/sys` | kobject → 目录/文件 |
| **④ 内核事件层** | uevent | netlink 通知用户态 |
| **⑤ 内核模块** | loadable modules | 驱动热插拔基础 |

---

### ① 设备类型 · Device Types

Unix/Linux 将设备分为几类（+ 扩展）：

| 类型 | 访问方式 | 特点 | 示例 |
|------|----------|------|------|
| **块设备（block）** | **块设备节点** · 常挂载 FS | **固定块大小** · **可随机寻址（seek）** | 硬盘、SSD、蓝光、闪存 |
| **字符设备（character）** | **字符设备节点** | **字节流** · **不可寻址** | 键盘、鼠标、串口 |
| **网络设备（network）** | **非设备节点** — **`socket` API** | 物理网卡 + 协议栈 | 以太网卡 |

#### 扩展类型

| 类型 | 说明 |
|------|------|
| **杂项设备（misc）** | **字符设备的简化** — 表示简单小驱动 |
| **伪设备（pseudo）** | **内核虚拟功能** — 非物理硬件 |

| 伪设备示例 | 作用 |
|------------|------|
| **`/dev/null`** | 黑洞 — 丢弃写入 |
| **`/dev/random` / `urandom`** | 随机数 |

```
「一切皆文件」：
  block/char ──► /dev/sda、/dev/ttyS0 ──► open/read/write
  network    ──► 打破该原则 ──► socket()
```

→ [Ch 1](./chapter-01-Linux内核简介.md) · [Ch 13](./chapter-13-虚拟文件系统.md) · [Ch 14](./chapter-14-块IO层.md)

**HFT：** 行情路径走 **网卡 + socket/DPDK**；配置/调优常读 **`/sys/class/net/...`**。

---

### ② 统一设备模型 · The Device Model

**动机（2.6）：** 构建准确 **设备拓扑树** → **设备级电源管理**（例：关 USB 控制器前须先关 USB 鼠标）。

| 需求 | 统一表示设备 + 描述 **父子/总线** 关系 |

#### 核心组件

| 组件 | 角色 |
|------|------|
| **`kobject`** | **最核心** — 像 OOP **基类**；引用计数、名称、**父指针** → **层次结构** |
| **`ktype`** | 描述一族 kobject 的 **默认行为** — 析构、sysfs 操作、默认属性 |
| **`kset`** | **kobject 集合** — 容器（如「所有块设备」一组） |
| **`kref`** | **标准引用计数** — 用则增、完则减；**归零安全销毁** |

#### 嵌入式设计（同 list_head）

| 模式 | 说明 |
|------|------|
| `kobject` **嵌入** `cdev` 等 | 给驱动结构 **面向对象 + sysfs 生命周期** |

```
USB 控制器 kobject
    └── USB Hub kobject
            └── 鼠标 kobject    ← 关电须自底向上
```

→ **Ch 6** 嵌入结构 · **Ch 12** kref 与内存释放

---

### ③ sysfs 虚拟文件系统

| 属性 | 说明 |
|------|------|
| **本质** | 内存中 **VFS** — 把 **kobject 层次** 导出到用户态 |
| **挂载点** | 通常 **`/sys`** |
| **映射** | kobject → **目录** · 属性（attributes）→ **文件** |

```
/sys/block/nvme0n1/queue/scheduler
/sys/class/net/eth0/...
/sys/devices/pci0000:00/...
```

| 用途 | 查看 **拓扑** · **读写驱动参数** · 脚本调优 |

**HFT 示例：**

| 路径 | 调什么 |
|------|--------|
| `/sys/block/*/queue/scheduler` | I/O 调度器（Ch 14） |
| `/sys/class/net/*/queues/...` | RSS/RPS 等（→ Rosen Ch14） |

→ [02 SysPerf Ch9 scheduler](../../02-Systems-Performance-2nd/chapter-09-disks/notes/section-9.4-硬件与软件架构.md) · [Ch 5](./chapter-05-系统调用.md) **优先 sysfs 而非新 syscall**

---

### ④ 内核事件层 · Kernel Events Layer

建立在 **kobject** 之上的 **内核 → 用户** 通知。

| 模型 | 从某 **kobject**（对应 **sysfs 路径**）发出 **事件** |
|------|------------------------------------------------------|
| 动作字符串 | 如 **`add`**、**`remove`** |
| 传递 | **netlink** 套接字 → 用户态（**udev/systemd-udevd**） |

```
热插拔 U 盘
    ▼
内核 kobject 注册 + uevent("add")
    ▼
udev 监听 netlink ──► 创 /dev 节点、挂载策略…
```

| 用户态 | **udev rules** — 绑 IRQ、权限、符号链接 |

---

### ⑤ 内核模块 · Modules

Linux = **宏内核**，但支持 **可加载模块** — 运行时 **插入/移除** 对象代码。

| 作用 | 说明 |
|------|------|
| **设备驱动** | 按需 `modprobe` — 无硬件时不占内核 |
| **热插拔** | 总线探测 → 加载对应模块 |
| 不限于驱动 | 文件系统、协议等也可模块化 |

| 用户命令 | 说明 |
|----------|------|
| **`insmod` / `modprobe`** | 加载 |
| **`rmmod`** | 卸载 |
| **`lsmod`** | 列出 |

→ **Ch 2** 编译安装 · `make modules_install` → `/lib/modules/`

```bash
# 概念
modprobe ixgbe          # 加载网卡驱动模块
cat /sys/module/ixgbe/parameters/...
```

**HFT：** 定制 **网卡驱动模块**、**内核参数** 与 **`/sys/module/.../parameters`** — 生产变更需可回滚。

---

### 设备栈总览（与前面章节）

```
应用
  ├─ open("/dev/sdX")     ──► 块层（Ch 14）──► 驱动模块
  ├─ open("/dev/uio")     ──► 字符驱动 / UIO
  └─ socket()             ──► 网络子系统（非 /dev）
         ▲
    sysfs / uevent 暴露拓扑与配置
```

---

### Ch 17 小结

| 问题 | 答案 |
|------|------|
| 三种主设备？ | **块 · 字符 · 网络（socket）** |
| 网络为何特殊？ | **非**「一切皆文件」设备节点 |
| 设备模型核心？ | **kobject / ktype / kset / kref** |
| sysfs？ | kobject 树 → **`/sys`** |
| uevent？ | **netlink** 通知 udev 等 |
| 模块？ | 宏内核的 **动态扩展** · 驱动热插拔 |

---

### 检查单

- [ ] 区分 **块设备 seek** 与 **字符字节流**
- [ ] 解释 **kobject 嵌入 cdev** 的意义
- [ ] 说出 **sysfs 目录/文件** 与 kobject/属性的对应
- [ ] 描述 **uevent → udev** 热插拔链
- [ ] 知 **misc / 伪设备** 各一例
- [ ] HFT：能举 **`/sys` 下调网卡/块设备** 的路径

---

## 相关章节

- 上一章：[chapter-16-页高速缓存和页回写.md](./chapter-16-页高速缓存和页回写.md)
- 下一章：[chapter-18-调试.md](./chapter-18-调试.md)
- 本模块导读：[README.md](./README.md) · [OUTLINE.md](./OUTLINE.md)
