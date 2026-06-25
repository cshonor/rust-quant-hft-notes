# Ch 5 bpftrace · bpftrace

> **BPF Performance Tools** · Brendan Gregg · **精读 🔴**

> 本章定位：**ad hoc 排障与短脚本的入口** — 若 [Ch 4 BCC](./chapter-04-BCC.md) 是写复杂工具、守护进程的 **重型武器**，bpftrace 则适合 **临时验证假设、单行命令 (one-liners)、几十行短脚本**。语法类似 **awk + C**，大幅降低 eBPF 门槛。  
> **HFT：** BCC runbook 定方向后，用 bpftrace **几分钟内** 验证「是不是这个 syscall / 这个 PID / 这条栈」— 比起完整 BCC Python 项目快一个数量级；仍须遵守 **内核聚合、短窗口** 原则。  
> **上一章：** [chapter-04-BCC.md](./chapter-04-BCC.md) · **下一章：** [chapter-06-CPU.md](./chapter-06-CPU.md)

---

## 1. bpftrace 是什么

| 对比 | **BCC** | **bpftrace** |
|------|---------|--------------|
| **典型形态** | Python + 嵌入 BPF C、70+ 预置工具 | **一门脚本语言** + CLI |
| **上手成本** | 读 man、理解工具参数 | 单行即可开测 |
| **适合** | 生产 runbook、复杂多探针工具 | **ad hoc**、假设验证、教学演示 |
| **本书** | [Ch 4](./chapter-04-BCC.md) | **本章** |

**全书分工：** Ch 3 清单 → Ch 4 BCC 工具箱 → **本章语言** → Ch 6+ 按资源域（CPU/内存/网络…）展开 **具体场景与工具**。

---

## 2. 核心架构与编译流程

```
bpftrace 脚本 (.bt 或 -e '...')
    → lex/yacc 解析语言 → AST
    → Clang 解析 C 结构体（tracepoint 参数等）
    → LLVM IR → BPF 字节码
    → bpf() 加载 + 附加探针
    → 用户态：结束时打印 @map / 实时 printf
```

| 阶段 | 组件 | 作用 |
|------|------|------|
| 前端 | lex / yacc | 解析 `probe /filter/ { actions }` |
| 类型 | Clang | 内核 struct、tracepoint 字段布局 |
| 后端 | LLVM | IR → 验证器可接受的 BPF 字节码 |
| 运行时 | 内核 BPF VM + Map | 探针触发 → 聚合或打印 |

```bash
bpftrace --version
bpftrace -e 'BEGIN { printf("hello\n"); }'
```

---

## 3. 全栈事件源 (Probes)

bpftrace **可见性极高** — 同一套语法可挂多种事件源：

| 类型 | 前缀/形式 | 说明 |
|------|-----------|------|
| **kprobe** | `kprobe:func` | 内核函数入口 |
| **kretprobe** | `kretprobe:func` | 内核函数返回 |
| **uprobe** | `uprobe:path:func` | 用户态函数入口 |
| **uretprobe** | `uretprobe:path:func` | 用户态函数返回 |
| **tracepoint** | `tracepoint:cat:event` | 内核静态追踪点（稳定、推荐） |
| **usdt** | `usdt:path:probe` | 用户态静态探针 |
| **profile** | `profile:hz:99` | 定时 CPU 采样 |
| **interval** | `interval:s:1` | 定时在用户态执行动作 |
| **software** | `software:faults:1000` | 软 PMU 事件 |
| **hardware** | `hardware:cache-misses:1000` | 硬 PMU 事件 |

**通配符：** 逗号绑定多探针；`kprobe:vfs_*` 匹配所有 `vfs_` 前缀内核函数（注意开销）。

```bash
# 多探针
bpftrace -e 'kprobe:vfs_read,kprobe:vfs_write { @[comm] = count(); }'

# tracepoint（字段名因内核版本而异，先用 bpftrace -l 列出）
bpftrace -e 'tracepoint:syscalls:sys_enter_openat { @ = count(); }'
```

→ 探针原理：[Ch 2 § 插桩](./chapter-02-技术背景.md)

---

## 4. 编程语法结构

基本形式：

```c
probes /filter/ { actions }
```

| 部分 | 说明 | 示例 |
|------|------|------|
| **Probes** | 事件触发点 | `kprobe:do_sys_open` |
| **Filter** | 可选布尔条件，为真才执行动作 | `/pid == 12345/` |
| **Actions** | `{ }` 内语句，分号分隔 | `@ = count();` |

**完整示例：**

```bash
bpftrace -e '
kprobe:vfs_read
/pid == $1/
{
    @bytes = sum(arg2);
}
' $(pidof myapp)
```

| 语法糖 | 含义 |
|--------|------|
| `BEGIN` | 脚本启动时执行一次（初始化） |
| `END` | 脚本退出前执行（收尾打印） |
| `interval:s:5` | 每 5 秒触发（看实时计数） |

---

## 5. 三大变量类型

### 内置变量 (Built-in)

探针触发时 **只读** 的上下文 — 无需声明：

| 变量 | 含义 |
|------|------|
| `pid` | 进程 ID |
| `tid` | 线程 ID |
| `comm` | 进程名（16 字符截断） |
| `uid` / `gid` | 用户/组 |
| `nsecs` | 纳秒时间戳（单调时钟） |
| `elapsed` | 距脚本启动纳秒数 |
| `cpu` | 当前 CPU 编号 |
| `retval` | **kretprobe/uretprobe** 返回值 |
| `arg0`…`arg5` | 探针参数（位置因探针类型而异） |
| `kstack` | 内核栈（配合 `print(kstack)` 或作 map 键） |
| `ustack` | 用户栈 |

### 临时变量 (Scratch) — `$` 前缀

当前动作块内 **局部** 计算：

```bash
bpftrace -e '
kprobe:tcp_sendmsg
{
    $size = arg2;
    @total = sum($size);
}
'
```

### 映射表 (Maps) — `@` 前缀

**跨事件存储与关联的核心** — 底层即 BPF Map：

```bash
# 按线程记录开始时间
@start[tid] = nsecs;

# 按 comm 计数
@[comm] = count();

# 全局单值
@bytes = sum(arg2);
```

| 键类型 | 用途 |
|--------|------|
| 标量 `@x` | 全局计数/求和 |
| `@x[key]` | 按 PID、comm、栈 ID 等维度聚合 |
| 嵌套 `@x[a,b]` | 二维统计 |

**程序结束** 时，bpftrace **默认自动打印** 所有 `@` map 内容（可用 `print()` 自定义时机）。

---

## 6. Map 聚合函数

海量事件 **在内核完成统计**，不把每条记录送到用户态：

| 函数 | 作用 |
|------|------|
| `count()` | 事件次数 |
| `sum(expr)` | 求和 |
| `avg(expr)` | 平均值 |
| `min()` / `max()` | 极值 |
| `stats(expr)` | count + sum + avg + min + max |
| `hist(expr)` | **2 的幂次方** 直方图（延迟分布首选） |
| `lhist(expr, min, max, step)` | **线性** 直方图 |

```bash
# 读延迟分布（enter/exit 配对示意）
bpftrace -e '
kprobe:vfs_read
/@start[tid]/
{
    @us = hist(nsecs - @start[tid]);
    delete(@start[tid]);
}
kprobe:vfs_read
{
    @start[tid] = nsecs;
}
'

# 按进程统计 syscall 次数
bpftrace -e 'tracepoint:syscalls:sys_enter_* { @[comm] = count(); }'
```

**HFT：** 延迟问题优先 `hist()` / `lhist()` — 与 [Ch 3](./chapter-03-性能分析.md)「直方图优于均值」一致；勿对 `send`/`recv` 每包 `printf`。

---

## 7. 常用内置函数

| 函数 | 作用 |
|------|------|
| `printf(fmt, ...)` | 格式化输出（类似 C） |
| `time(fmt)` | 人类可读时间戳 |
| `join(arr, delim)` | 拼接字符串数组（如 `argv`） |
| `str(ptr)` | 安全读用户/内核内存为字符串 |
| `ksym(addr)` | 内核地址 → 符号名 |
| `usym(addr)` | 用户地址 → 符号名 |
| `kstack` / `ustack` | 栈 ID 或配合 `print(kstack)` |
| `cat(path)` | 读文件内容到字符串（脚本初始化） |
| `system()` | 用户态执行 shell（**慎用**，仅 BEGIN/END） |

```bash
bpftrace -e 'kretprobe:sys_read /@bytes[comm] = sum(retval);/'
bpftrace -e 'tracepoint:syscalls:sys_enter_execve {
    printf("%s %s\n", comm, str(args->filename));
}'
```

---

## 8. 控制流限制

BPF **验证器** 要求程序 **有界、可终止** — 禁止内核死循环。

| 允许 | 禁止 |
|------|------|
| `/filter/` 布尔过滤 | `while (1)` 等无限循环 |
| `if / else` | 无界 `for` |
| 三元 `? :` | 递归 |
| `unroll(N) { ... }` | N 必须 **编译期常量** |

```bash
bpftrace -e '
kprobe:foo
{
    unroll(4) {
        @ = count();
    }
}
'
```

**实践：** 复杂状态机用 **多个探针 + map** 拆分，而非循环。

---

## 9. 调试与排障

| 方法 | 命令/做法 | 何时用 |
|------|-----------|--------|
| **`printf` 调试** | 在动作里 `printf("hit %d\n", pid);` | 最快确认探针是否触发 |
| **`-d`** | 打印 AST、LLVM IR | 语法/类型/编译问题 |
| **`-v`** | 打印最终 BPF 字节码指令 | 验证器拒绝、与预期不符 |
| **`-l 'pattern'`** | 列出可用探针 | 找 tracepoint 全名 |
| **`--btf`** | 使用 BTF（若可用） | 结构体字段、CO-RE 路径 |

```bash
bpftrace -dl 'kprobe:*read*'
bpftrace -dv -e 'BEGIN { @ = count(); }'
```

| 常见问题 | 排查 |
|----------|------|
| 无输出 | 过滤器太严？探针名错？用 `printf` 确认触发 |
| 验证器失败 | 减栈深度、减 map 大小、避免非法指针解引用 |
| 字段不存在 | 内核版本差异 — `bpftrace -l` + 查 tracepoint format |

→ BCC 侧调试：[Ch 4 § 调试](./chapter-04-BCC.md) · SysPerf 单行：[appendix-A](./appendix-A-bpftrace单行命令.md)

---

## 10. 经典 One-Liners 速览

以下可在 **数秒** 内验证假设；完整清单见 [附录 A](./appendix-A-bpftrace单行命令.md) 与 [附录 B 备忘单](./appendix-B-bpftrace备忘单.md)。

```bash
# 谁在读盘（按进程计数）
bpftrace -e 'tracepoint:syscalls:sys_enter_read { @[comm] = count(); }'

# 新进程
bpftrace -e 'tracepoint:syscalls:sys_enter_execve { printf("%s %s\n", comm, str(args->filename)); }'

# 每 CPU 采样栈（CPU 热点）
bpftrace -e 'profile:hz:99 { @[kstack] = count(); }'

# TCP 连接（示意，字段随内核版本调整）
bpftrace -e 'kprobe:tcp_connect { printf("connect pid=%d\n", pid); }'

# 某 PID 的 open 路径
bpftrace -e 'tracepoint:syscalls:sys_enter_openat /pid == 1234/ {
    printf("%s\n", str(args->filename));
}'
```

**HFT 用法：** incident 窗口内 **短跑 30–60s** → 确认嫌疑 → 再换 BCC 工具（`runqlat`、`profile-bpfcc`）长一点采集。

---

## 11. Part II 预告（Ch 6+）

从 **第 6 章** 起进入 **「使用 BPF 工具」** — 按资源域展开：

| 章 | 主题 | HFT 关联 |
|----|------|----------|
| [Ch 6 CPU](./chapter-06-CPU.md) | `runqlat`、`profile`、调度 | 绑核、排队延迟 |
| [Ch 7 内存](./chapter-07-内存.md) | `memleak`、`slab` | 较少热路径，OOM 排查 |
| [Ch 10 网络](./chapter-10-网络.md) | `tcpretrans`、`tcpconnect` | 共置机网络栈 |

**学习顺序：** 本章语法 → **Ch 6 CPU**（与 Ch 3 清单衔接最紧）→ Ch 10 网络。

---

## 12. HFT 读者 Takeaway

1. **bpftrace = 假设验证加速器** — BCC runbook 之后、改代码之前的 **5 分钟层**。
2. **语法核心：** `probe /filter/ { @map = agg(); }` — 内置变量 + `$` 临时 + `@` 聚合。
3. **高频事件只用 Map 函数**（`count`、`hist`）— `printf` 仅低频或调试。
4. **`kstack`/`ustack` + `profile`** 与 BCC `stackcount`/`profile` 同族 — 火焰图仍见 [Ch 2](./chapter-02-技术背景.md)。
5. **无无限循环** — 用多探针 + map 表达状态；`unroll(N)` 有界展开。
6. 排障链：**`-l` 找探针 → `printf` 确认 → `-d`/`-v` 查编译**；生产热路径 **限时、限 PID、限核**。

---

## 相关章节

- 上一章：[chapter-04-BCC.md](./chapter-04-BCC.md)
- 下一章：[chapter-06-CPU.md](./chapter-06-CPU.md)
- 技术地基：[chapter-02-技术背景.md](./chapter-02-技术背景.md)
- 方法论与清单：[chapter-03-性能分析.md](./chapter-03-性能分析.md)
- 附录 A 单行命令：[appendix-A-bpftrace单行命令.md](./appendix-A-bpftrace单行命令.md)
- 附录 B 备忘单：[appendix-B-bpftrace备忘单.md](./appendix-B-bpftrace备忘单.md)
- SysPerf bpftrace：[appendix-C-bpftrace单行命令](../02-Systems-Performance-2nd/appendix-C-bpftrace单行命令.md)
