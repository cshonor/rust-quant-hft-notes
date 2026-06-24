# Ch 18 · 调试 · Debugging

> **Linux Kernel Development 3rd** · Robert Love · **选读**  
> 本章定位：内核 **缺 gdb 便利、小错即崩** — `printk`、**Oops**、**BUG_ON**、SysRq、kgdb、探测技巧、**git bisect**。写驱动/改内核前的 **救命工具箱**。

---

## 本节结构

| 节 | 主题 | 带走什么 |
|----|------|----------|
| **① printk** | 打印调试 | 日志级 · 环形缓冲 |
| **② Oops** | 严重错误 | panic vs 杀进程 |
| **③ 编译选项** | Kernel Hacking | sleep-in-spinlock 检测 |
| **④ 断言与栈** | BUG / panic | `dump_stack` |
| **⑤ SysRq** | 魔法键 | s-u-b 救命 |
| **⑥ 调试器** | gdb / kgdb | kcore 只读 |
| **⑦ 探测技巧** | UID / ratelimit | 二分 Git |

---

### 为何内核调试更难

| 用户空间 | 内核空间 |
|----------|----------|
| gdb、core dump | 一点错 → **Oops / panic** |
| 进程隔离 | **整机** 受影响 |
| 可频繁打印 | `printk` 淹没或 **拖死** 系统 |

→ **Ch 2** 无内存保护 · **Ch 5** 进程 vs 中断上下文

---

### ① 通过打印调试 · `printk()`

#### `printk()`

| 属性 | 说明 |
|------|------|
| **最常用** 内核调试手段 | |
| **几乎随时安全** | 中断上下文、持锁、SMP |
| 局限 | **控制台初始化前** 无输出 → 早期用 **`early_printk()`**（非跨平台） |

```c
printk(KERN_INFO "device probed: %d\n", id);
```

→ **Ch 2** `printk` vs `printf`

#### 日志等级 · Loglevels

| 宏示例 | 严重程度 |
|--------|----------|
| **`KERN_EMERG`** | 最高 — 系统不可用 |
| **`KERN_WARNING`** | 警告 |
| **`KERN_DEBUG`** | 调试 |

| 行为 | 由 **当前控制台日志等级** 决定是否 **输出到物理终端** |

用户态查看：`dmesg` · `/var/log/kern.log`（经 **rsyslog/journald**）

#### 记录缓冲区 · Log Buffer

| 设计 | 说明 |
|------|------|
| **环形缓冲区** | 单核时代常见 **~16KB**（现可更大） |
| 满则 **覆盖最旧** | 内存可控 |
| 中断里 **无阻塞写** | |

| 用户态 | 历史 **`klogd`** + **`syslogd`** 读缓冲写文件 — 现多 **journald** |

**HFT：** 生产内核 **少 printk 热路径** — 用 **tracepoint/BPF**（→ SysPerf Ch14/15）或 **动态 debug**。

---

### ② Oops

**Oops** = 内核报告 **无法处理的异常**（如 **空指针解引用**）。

| 输出内容 | 错误信息 · **寄存器** · **调用栈 backtrace** |
|----------|-----------------------------------------------|

#### 致命程度

| 发生位置 | 后果 |
|----------|------|
| **中断上下文**、**idle (pid 0)**、**init (pid 1)** | 无法继续 → **`panic()`** · **整机挂死** |
| **普通用户进程** 上下文 | 通常 **杀死该进程** · 内核 **尝试继续** |

#### 解码 Oops

| 时代 | 工具 |
|------|------|
| 早期 | **`ksymoops`** + **`System.map`** — 手动 **地址 → 符号** |
| **2.6+ `kallsyms`** | `CONFIG_KALLSYMS` — 符号表编进内核 → **直接可读 backtrace** |

```
Oops: 0000 [#1] SMP
Call Trace:
 [<ffffffffa0123456>] my_drv_ioctl+0x42/0x100 [mydrv]
 ...
```

---

### ③ 内核调试选项 · Kernel Hacking

`make menuconfig` → **Kernel Hacking**（依赖 **`CONFIG_DEBUG_KERNEL`**）

| 功能示例 | 作用 |
|----------|------|
| **sleep-inside-spinlock 检测** | 在 **原子上下文**（持 spinlock / 关抢占）**非法睡眠** → 抓 **死锁元凶** |

→ **Ch 9–10** 自旋锁 vs mutex 上下文规则

| 现代补充 | **LOCKDEP**、**KASAN**、**KFENCE** — 书中未详述，方向一致 |

---

### ④ 引发 Bug 与打印信息

| 宏/函数 | 行为 |
|---------|------|
| **`BUG()` / `BUG_ON(cond)`** | 条件真 → **故意 Oops** · 栈回溯 · 终止当前操作 |
| **`panic()`** | **更致命** — 打印后 **挂起整机** |
| **`dump_stack()`** | 只 **打印栈** — **不杀进程、不 panic** — 日常路径跟踪 |

```c
BUG_ON(ptr == NULL);           /* 绝不应发生 */
if (debug) dump_stack();       /* 我在哪？ */
```

| 选用 | |
|------|--|
| 开发断言 | `BUG_ON` |
| 生产可恢复 | `WARN_ON`（书中相关）/ 错误码返回 |
| 跟踪流 | `dump_stack` |

---

### ⑤ 神奇的 SysRq 键 · Magic SysRq

**`CONFIG_MAGIC_SYSRQ`** — 系统 **死锁/假死** 时仍可向内核发 **底层命令**。

| x86 组合 | **`Alt + SysRq(PrtSc) + 字母`** |

| 命令 | 含义 |
|------|------|
| **`SysRq-s`** | **sync** — 脏缓冲写盘 |
| **`SysRq-u`** | **umount** — 卸载 FS |
| **`SysRq-b`** | **reboot** — 立即重启（**未 sync 会丢数据**） |

| 救命序列（经典） | **`s` → `u` → `b`** — 尽量安全重启 |

```
系统无响应但 SysRq 仍通
    ▼
s（落盘）→ u（卸盘）→ b（重启）
```

**HFT 实盘：** 慎用；Prefer **优雅下线** — 懂即可。

---

### ⑥ 内核调试器

#### gdb + `/proc/kcore`

| 能力 | **只读** 窥探 **运行中** 内核内存 |
|------|-----------------------------------|
| 不能 | 改数据 · **断点** · 单步 |

#### kgdb

| 方式 | **双机** · **串口** 连接 |
|------|-------------------------|
| 能力 | 完整 **远程 gdb** — 断点、单步、改变量 |

| 场景 | 深坑驱动 / 启动早期 — 实验室环境 |

→ 日常开发更多 **printk + ftrace + BPF**（[SysPerf Ch14 ftrace](../../02-Systems-Performance-2nd/chapter-14-ftrace/)）

---

### ⑦ 探测系统 · Poking and Probing

#### 用 UID 做条件开关

重写核心路径时：

```c
if (current_uid().val != 7777)
    old_fork_path();
else
    new_fork_path();   /* 仅测试用户走新代码 */
```

| 目的 | 新代码 bug **不拖垮全体用户** |

#### 限制打印频率

| 手段 | 说明 |
|------|------|
| **`printk_ratelimit()`** | 限制 **同一消息** 打印速率 |
| **发生次数限制** | 静态计数 — **仅前 N 次** `printk` |

| 问题 | 高频 ISR 里 `printk` → **控制台洪水** → **系统卡死** |

→ **Ch 7** ISR 要快 · **Ch 2** 不要用 `printf`

---

### ⑧ 二分法查找 · `git bisect`

| 场景 | 当前版本有 bug，不知 **哪次提交** 引入 |
|------|----------------------------------------|
| 方法 | 找 **已知好** 与 **已知坏** commit → **二分测试** |

```bash
git bisect start
git bisect bad          # 当前坏
git bisect good v4.19   # 已知好标签
# 反复：编译/测试 → git bisect good|bad
git bisect reset
```

→ **Ch 2** `git clone` 内核树 · **Ch 20** 补丁流程

---

### Ch 18 小结

| 工具/概念 | 何时用 |
|-----------|--------|
| **`printk` + loglevel** | 第一手、任意上下文 |
| **环形 log buffer** | `dmesg` / journal |
| **Oops + kallsyms** | 崩溃后读栈 |
| **BUG_ON / panic** | 断言 / 致命停 |
| **`dump_stack`** | 非致命路径跟踪 |
| **SysRq s-u-b** | 死机前尽量落盘 |
| **kgdb** | 全功能远程调试 |
| **`printk_ratelimit`** | 高频路径 |
| **`git bisect`** | 回归哪次提交 |

---

### 检查单

- [ ] 说出 **`printk` 在中断里可用** 但 **`malloc(GFP_KERNEL)` 不可用**
- [ ] 区分 **Oops 杀进程** vs **panic 挂机**
- [ ] 解释 **`kallsyms`** 为何能直接读符号栈
- [ ] 背 **SysRq s / u / b** 含义与顺序
- [ ] 知 **`dump_stack` vs BUG_ON`** 区别
- [ ] 会用 **`git bisect`** 概念流程

---

## 相关章节

- 上一章：[chapter-17-设备与模块.md](./chapter-17-设备与模块.md)
- 下一章：[chapter-19-可移植性.md](./chapter-19-可移植性.md)
- 观测：[02 SysPerf Ch14 ftrace](../../02-Systems-Performance-2nd/chapter-14-ftrace/) · [Ch15 BPF](../../02-Systems-Performance-2nd/chapter-15-bpf/)
- 本模块导读：[README.md](./README.md) · [OUTLINE.md](./OUTLINE.md)
