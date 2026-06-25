# Ch 4 BCC · BCC (BPF Compiler Collection)

> **BPF Performance Tools** · Brendan Gregg · **精读 🔴**

> 本章定位：**BCC 工具箱使用说明书 + 多用途工具内部逻辑** — BPF 的 **主要前端项目**，含 **70+** 开箱即用性能/排障工具。读懂本章，才能从「跑现成脚本」过渡到「用 BCC 写自己的 BPF 工具」。  
> **HFT：** 生产环境 **内核侧粗筛与下钻** 的主力载体（`runqlat`、`profile`、`tcpretrans` 等多为 BCC 实现）；理解 **单用途 vs 多用途** 与 **内核聚合 vs 逐行打印**，避免在热路径上误用 `trace`。  
> **上一章：** [chapter-03-性能分析.md](./chapter-03-性能分析.md) · **下一章：** [chapter-05-bpftrace.md](./chapter-05-bpftrace.md)

---

## 1. BCC 是什么

| 维度 | 说明 |
|------|------|
| **定位** | 构建 BPF 软件的 **开源编译器框架 + 工具集** |
| **前端语言** | Python、C++、Lua |
| **编译链** | **Clang/LLVM** 将 BPF C 编译为字节码 → `bpf()` 注入内核 |
| **规模** | **70+** 单用途工具 + 若干多用途「瑞士军刀」 |

**与全书关系：** [Ch 2](./chapter-02-技术背景.md) 讲 VM/Map/探针原理；[Ch 3](./chapter-03-性能分析.md) 给 BCC 工具 **检查清单**；本章讲 **BCC 生态本身** 与四大多用途工具；[Ch 5](./chapter-05-bpftrace.md) 讲更轻量的 **bpftrace** 脚本语言。

---

## 2. BCC 架构与特性

### 编译与加载流程

```
用户脚本 (Python 等)
    → 嵌入 BPF C 源码
    → Clang/LLVM 编译为 BPF 字节码
    → bpf() 系统调用加载程序 + 创建 Map
    → 附加到 kprobe/uprobe/tracepoint/USDT 等
    → 用户态轮询/读取 Map，格式化输出
```

### 内核级能力

| 能力 | 典型用途 |
|------|----------|
| **动态 kprobes / uprobes** | 任意内核/用户函数插桩（需符号） |
| **Tracepoint** | 稳定、低开销的内核静态探针 |
| **BPF Map** | 直方图、频率计数、聚合 — **海量事件在内核汇总** |
| **栈回溯** | `bpf_get_stackid` + 栈 Map → `stackcount` / `profile` |

### 用户级能力

| 能力 | 说明 |
|------|------|
| **USDT** | 用户态静态探针（需应用带 SDT 探针，如某些数据库/语言运行时） |
| **debuginfo 符号解析** | 内核/用户栈、函数名 — 依赖 debug 包或 BTF |
| **Python 胶水** | 参数解析、输出格式化、与 CLI 集成 |

```bash
# 常见安装名（发行版差异）：bcc-tools / python3-bcc
ls /usr/share/bcc/tools/ | head
man opensnoop-bpfcc    # 或 bcc-opensnoop 等，视发行版而定
```

→ 自研工具深入：[appendix-C-BCC工具开发.md](./appendix-C-BCC工具开发.md) · C/libbpf 路线：[appendix-D-C语言BPF.md](./appendix-D-C语言BPF.md)

---

## 3. 单用途 vs 多用途：设计哲学

### 单用途工具 (Single-Purpose Tools)

遵循 **Unix 哲学**：**做好一件事**。

| 例子 | 只做 |
|------|------|
| `opensnoop` | 追踪 `open()` / `openat()` |
| `runqlat` | 进程 **等 CPU** 延迟分布 |
| `tcpretrans` | TCP 重传事件 |

| 优点 | 说明 |
|------|------|
| **零门槛** | 默认参数 + 默认输出即可排障 |
| **易维护** | 行为固定，文档即契约 |
| **低认知负担** | [Ch 3 BCC 清单](./chapter-03-性能分析.md) 可直接当 runbook |

**HFT：** incident 第一轮优先 **单用途 + 直方图类**（`runqlat`、`biolatency`、`tcpretrans`），不要一上来写自定义 BCC。

### 多用途工具 (Multi-Purpose Tools)

**极高灵活性** — 同一引擎可挂不同函数、tracepoint、USDT，减少为每个目标写一个新工具。

| 权衡 | 说明 |
|------|------|
| **学习曲线** | 需理解参数语义与输出格式 |
| **回报** | 跨组件自定义追踪，少重复造轮子 |

本章重点四个多用途工具见下节。

---

## 4. 四大多用途工具

### 选型速查

| 工具 | 回答什么 | 输出形态 | 适合事件频率 |
|------|----------|----------|--------------|
| **`funccount`** | 谁被调了多少次？ | 计数表 | **高** |
| **`stackcount`** | 哪些栈路径触发了事件？ | 栈 + 计数 → **火焰图** | **中高** |
| **`trace`** | 每次事件的细节（参数/返回值）？ | **逐行打印** | **低** |
| **`argdist`** | 参数/返回值分布？ | 频率或 **2 的幂直方图** | **中高** |

```
高频事件 ──────────────────────────────────────────► 低频事件
  funccount / argdist (内核 Map 聚合)     trace (逐行)
              stackcount (栈聚合)
```

### `funccount` — 事件频率统计

在内核 BPF 程序里对事件 **`++`**，结果存 Map；用户态只读汇总表。

```bash
# 统计内核函数调用次数（示例）
sudo funccount-bpfcc 'vfs_read'

# 统计 tracepoint
sudo funccount-bpfcc -t 'syscalls:sys_enter_read'

# 统计 USDT（若进程带探针）
sudo funccount-bpfcc -p $(pidof myapp) 'u:myapp:probe_name'
```

**要点：** 不把每条事件送到用户态 — **海量调用** 时仍可用。  
**HFT：** 验证「这条 syscall 是否在策略循环里被疯狂调用」；比 `strace` 轻，但仍非零开销，勿长期挂在最低延迟核。

### `stackcount` — 栈频率 + 火焰图

统计 **导致某事件的完整内核/用户栈** 及次数；输出可喂给 **火焰图 (Flame Graphs)**。

```bash
sudo stackcount-bpfcc -f 'vfs_write' > out.stacks
# 用 FlameGraph 工具折叠（书内 / Brendan Gregg 仓库）
```

**与 `profile` 区别（直觉）：**

| | `stackcount` | `profile` |
|---|--------------|-----------|
| **触发** | 你指定的 **事件**（如某函数入口） | **定时采样** CPU |
| **问题** | 「谁走了这条路径？」 | 「CPU 时间在哪儿？」 |

→ 火焰图原理：[Ch 2 § 火焰图](./chapter-02-技术背景.md)

### `trace` — 逐事件详情

打印 **每次** 命中的自定义信息：函数参数、返回值、时间戳等。

```bash
sudo trace-bpfcc -p $(pidof myapp) 'u:myapp:entry %d %s', arg1, arg2
```

| 适合 | 不适合 |
|------|--------|
| 低频路径、启动阶段、偶发错误 | 高频 `read`/`send`、每 tick 都触发的 probe |

**HFT：** 仅用于 **复现窗口内的短跑**（如单次下单路径验证）；高频路径用 `funccount` / `argdist` 或 bpftrace 聚合。

### `argdist` — 参数/返回值分布

在内核用 Map 做 **频率计数** 或 **2 的幂次方直方图** — 看「参数通常多大」。

```bash
# 分布：read() 的 count 参数
sudo argdist-bpfcc -C 'p::sys_read(size_t):size_t size'

# 直方图模式（示意，具体语法见 man）
sudo argdist-bpfcc -H 'p::malloc:u64'
```

**HFT：** 看 `recv` 长度分布、`write` 大小 — 判断是否在发大量小包（与 [Ch 10 网络](./chapter-10-网络.md) 衔接）。

---

## 5. 规范的工具文档

BCC 工具面向 **生产环境**：需 **root**，且每个工具都有标准文档。

### Man Pages（手册页）

| 内容 | 说明 |
|------|------|
| **原理** | 挂哪些 probe、内核里做什么聚合 |
| **开销估算** | 能否常驻、对延迟的大致影响 |
| **输出字段** | 每列含义 |
| **参数** | `-p` PID、`-c` 命令、`-d` 秒数、过滤表达式等 |

```bash
man funccount-bpfcc
man stackcount-bpfcc
```

### Examples Files（示例文件）

发行版通常在 `/usr/share/bcc/examples/doc/`（路径因包而异）：

| 特点 | 价值 |
|------|------|
| **真实命令 + 输出截图** | 比干读 man 更快建立直觉 |
| **逐段解读** | 对照「这一列说明什么」 |

**学习路径建议：** `man` 看参数 → `examples` 看场景 → 本机跑一遍 → 对照 [Ch 3 清单](./chapter-03-性能分析.md) 纳入 runbook。

---

## 6. BCC 调试与排障

工具 **编译失败**、**无输出**、**输出离谱** 时的手段。

### `bpf_trace_printk()` — 内核 printf

在 BPF C 里插入调试打印，从 trace pipe 读取：

```c
bpf_trace_printk("hit pid=%d\n", pid);
```

```bash
sudo cat /sys/kernel/debug/tracing/trace_pipe
# 或
sudo trace-cmd stream
```

**注意：** `printk` 格式有限、有开销；**调通后删除**。生产热路径禁用。

### Python 层 Debug Flags

在 BCC Python 脚本中开启（具体常量名以所用 bcc 版本为准）：

| 标志 | 作用 |
|------|------|
| `DEBUG_LLVM_IR` | 查看 LLVM IR |
| `DEBUG_BPF` | 预处理后的 BPF C、加载细节 |
| `DEBUG_SOURCE` | 源码与行号映射 |

用于：**验证 Clang 是否按预期编译**、**验证器拒绝原因**。

### 状态查看与清理

```bash
sudo bpftool prog list
sudo bpftool map list
# 部分环境
sudo bpflist-bpfcc
```

| 场景 | 做法 |
|------|------|
| 工具 **Ctrl-C 后探针残留** | 确认无孤儿 kprobe；必要时卸载模块或重启 tracing |
| **kprobe 过多** | 合并 probe、改用 tracepoint、缩短采集窗口 |
| **验证器失败** | 减循环、减栈深度、用 `bpf_probe_read` 替代直接解引用 |

→ 指令级：`bpftool prog dump` · [appendix-E-BPF指令.md](./appendix-E-BPF指令.md)

---

## 7. BCC vs bpftrace（预告）

| | **BCC** | **bpftrace** |
|---|---------|--------------|
| **形态** | Python + 嵌入 BPF C | **一门脚本语言** |
| **工具数量** | 70+ 预置 + 可自研 | 单行 ad hoc 极强 |
| **本书** | **本章** | [Ch 5](./chapter-05-bpftrace.md) |
| **HFT 分工** | runbook 固定工具、复杂多文件工具 | 验证假设、临时计数/直方图 |

**原则：** 先熟练 **单用途 BCC 清单** → 再学 **四个多用途** → 再用 **bpftrace** 补洞（附录 A）。

---

## 8. HFT 读者 Takeaway

1. **BCC = 生产级工具箱 + 可编程前端** — Ch 3 清单里的工具大多源于此生态。
2. **高频用聚合**（`funccount`、`argdist`、`runqlat` 类）— **低频用 `trace`**。
3. **`stackcount` + 火焰图** 找「哪条路径触发了异常 syscall/锁」；**`profile`** 找 CPU 热点 — 别混用场景。
4. **每个工具先读 man + examples** — 开销与字段含义比背命令重要。
5. 调试：**printk → debug flags → bpftool**；调通后去掉 printk，缩短采集窗口。
6. 最低延迟核上 **默认不常驻 BCC**；与 [DPDK 旁路](../14-DPDK-Low-Latency-Network/) 对比时，明确观测的是 **内核栈** 而非用户态 PMD 环。

---

## 相关章节

- 上一章：[chapter-03-性能分析.md](./chapter-03-性能分析.md)
- 下一章：[chapter-05-bpftrace.md](./chapter-05-bpftrace.md)
- 技术地基：[chapter-02-技术背景.md](./chapter-02-技术背景.md)
- BCC 自研：[appendix-C-BCC工具开发.md](./appendix-C-BCC工具开发.md)
- SysPerf BPF 章：[chapter-15-bpf](../02-Systems-Performance-2nd/chapter-15-bpf/)
- 网络工具实践：[chapter-10-网络.md](./chapter-10-网络.md)
