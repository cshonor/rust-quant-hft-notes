# Ch 2 技术背景 · Technology Background

> **BPF Performance Tools** · Brendan Gregg · **精读 🔴**

> 本章定位：**全书技术地基** — eBPF VM、Map、辅助函数、栈遍历、火焰图、四类插桩（k/u probe、Tracepoint/USDT）、PMC/perf。后续 BCC/bpftrace 工具都建在这些组件之上。  
> **HFT：** 读懂本章才能判断「这条 probe 为什么贵」「火焰图为什么缺帧」「换内核后脚本为何挂」— 避免在生产热路径上误用 per-event 输出。  
> **上一章：** [chapter-01-简介.md](./chapter-01-简介.md) · **下一章：** [chapter-03-性能分析.md](./chapter-03-性能分析.md)

---

## 1. BPF 与 eBPF

### 起源与演进

| 阶段 | 要点 |
|------|------|
| **经典 BPF** | BSD **包过滤器** — tcpdump 在内核过滤包，减少拷贝到用户态 |
| **eBPF（扩展 BPF）** | 2014+ 通用内核 VM — 寄存器 **2→10**、宽度 **32→64 bit**、**无上限 Map**、可调用 **helper**、经 **验证器** 保证安全 |

### 为什么性能工具需要 BPF

| 传统路径 | BPF 路径 |
|----------|----------|
| 海量事件 **拷贝到用户态** 再聚合 | **内核态** 过滤、计数、建直方图 |
| 高频率 syscall/trace 开销大 | 仅把 **聚合结果**（map、histogram）送到用户态 |

**例子：** `biolatency` 在内核按延迟桶 `++`，用户态只读 map 画图 — 不是每条 I/O 都上报。

### 开发、辅助函数与调试

| 组件 | 作用 |
|------|------|
| **BPF 程序** | C / LLVM → 字节码 → `bpf()` 加载 |
| **Helper** | 内核提供的安全 API，例如：`bpf_map_lookup_elem`、`bpf_probe_read`、`bpf_ktime_get_ns`、`bpf_get_stackid` |
| **bpftool** | 查看已加载程序、map、指令、`bpftool prog dump` 等 |

```bash
sudo bpftool prog list
sudo bpftool map list
```

### 前沿：BTF 与 CO-RE

| 技术 | 解决的问题 |
|------|------------|
| **BTF** (BPF Type Format) | 内核数据结构类型信息 — 供验证器与工具理解 layout |
| **CO-RE** (Compile Once – Run Everywhere) | 不同内核版本 **结构体偏移不同** — 编译期记录偏移，运行时 **relocate**，避免硬编码 `offsetof` |

→ 新工具链渐迁 **libbpf + CO-RE**；本书 BCC 仍大量可用，见 [appendix-D-C语言BPF.md](./appendix-D-C语言BPF.md)。

---

## 2. 堆栈追踪遍历 (Stack Trace Walking)

理解事件 **从哪条代码路径来** — `profile`、`offcputime`、栈采样都依赖栈回溯。

| 方法 | 原理 | 备注 |
|------|------|------|
| **帧指针 (Frame Pointer)** | x86-64：`RBP` 链 + 固定偏移 walk 栈帧 | **最快**；需 `-fno-omit-frame-pointer`（或 distro 默认保留） |
| **DWARF / debuginfo** | 调试信息解析栈 | 准但慢、需安装 debug 包 |
| **LBR** (Last Branch Record) | CPU 硬件记录最近分支 | 深度有限；Intel 常用 |
| **ORC** (Oops Rewind Capability) | 内核 unwind 元数据 | 内核栈常用；与用户态 DWARF 互补 |

> **HFT：** 发布二进制若 **省略帧指针**，火焰图会出现 `<unknown>` 或错误栈 — 与 [SysPerf Ch 6 CPU](../02-Systems-Performance-2nd/chapter-06-cpu/) 的 `-g` / FPO 讨论同构。策略 SO 建议 **保留 frame pointer** 或配 USDT/静态探针。

```bash
# 检查内核是否启用 ORC（现代发行版常见）
grep CONFIG_UNWINDER_ORC /boot/config-$(uname -r)
```

---

## 3. 火焰图 (Flame Graphs)

Gregg 发明的 **栈 profile 可视化** — 把成千上万行栈折叠成一张图。

| 轴 | 含义 |
|----|------|
| **X 轴（宽度）** | 该栈路径 **样本占比** — 越宽 = CPU（或 off-CPU）时间越多 |
| **Y 轴（高度）** | **栈深度** — 底 = 根（如 `_start` / 内核入口），顶 = 叶子（实际干活的函数） |

**读法：** 找 **最宽的平台** — 即首要瓶颈路径；点击（交互版）可 zoom。

**与 BPF：** BCC `profile`、bpftrace `@[kstack]` / `stack()` 输出可喂给 `flamegraph.pl` — 与 `perf record` 火焰图 **同一套阅读逻辑**。

→ [SysPerf Ch 6 火焰图](../02-Systems-Performance-2nd/chapter-06-cpu/) · 工具 `stackcollapse` + `flamegraph.pl`

---

## 4. 动态插桩：kprobes 与 uprobes

### kprobes（内核）

| 要点 | 说明 |
|------|------|
| **机制** | 在 **几乎任意内核指令** 动态插桩（x86_64 常用 `int3` 断点） |
| **触发** | 命中时跑 BPF 程序 — 可读上下文、写 map |
| **能力** | 深度透视 **未导出** 的内核路径 |
| **风险** | 内核内部函数 **无稳定 ABI** — 升级可能断；高频 probe 有开销 |

### uprobes（用户态）

| 要点 | 说明 |
|------|------|
| **机制** | 在用户二进制/共享库指令上插桩 — 类似 kprobes |
| **用途** | 追 `malloc`、自定义 SO 函数、语言 runtime |
| **警告** | **极高频** 函数（如每次 `malloc`）attach 可 **显著拖慢** — HFT 热路径慎用 per-hit 逻辑 |

**原则：** 能 **Tracepoint/USDT** 就不用 kprobe/uprobe；动态 probe **未 attach 时零开销**。

---

## 5. 静态插桩：Tracepoints 与 USDT

比动态插桩 **API 稳定、可预期**。

### Tracepoints（内核）

| 要点 | 说明 |
|------|------|
| **定义** | 内核开发者 **预埋** 的观测点（如 `sched:sched_process_exec`、`syscalls:sys_enter_openat`） |
| **优势** | **稳定名称**、有 **format** 文件描述字段 — bpftrace/BCC 首选 |
| **优先序** | **Tracepoint > kprobe**（当两者都能表达同一事件时） |

```bash
ls /sys/kernel/debug/tracing/events/sched/
cat /sys/kernel/debug/tracing/events/sched/sched_process_exec/format
```

### USDT（用户态静态探针）

| 要点 | 说明 |
|------|------|
| **定义** | 应用编译期插入探针 — 无 tracer attach 时多为 **`nop`**，**零开销** |
| **例子** | MySQL、Node.js、部分 C++ 框架 |
| **JIT 语言** | Java 等需 **动态 USDT** / 特殊 agent — 见 [chapter-12-语言.md](./chapter-12-语言.md) |

```bash
# 列出进程 USDT（若有）
sudo bpftrace -l 'usdt:*' 2>/dev/null | head
```

---

## 6. PMCs 与 perf_events

### PMC（Performance Monitoring Counters）

| 模式 | 行为 |
|------|------|
| **计数** | 累计某硬件事件（L3 miss、分支误预测、指令退休…） |
| **溢出采样** | 计数到阈值 → 中断 → 记录 **IP +（可选）栈** — `perf record` 基础 |

### PEBS（Intel Precise Event-Based Sampling）

**问题：** 普通 PMI 中断有 ** skid ** — 记录的 IP 不是真正触发事件的那条指令。  
**PEBS：** 硬件 **更精确** 地关联事件与指令指针 — 微架构级分析（cache、内存延迟）时重要。

**与 BPF：** BPF 可 **附加在 perf_event** 上（`BPF_PROG_TYPE_PERF_EVENT`）— 把 PMC 溢出与 map/栈收集结合；日常 HFT 更多直接用 `perf` + BCC `profile`，PMC 细节见 [chapter-06-CPU.md](./chapter-06-CPU.md)。

---

## 7. 技术组件地图（后文工具如何挂接）

```
                    ┌─────────────────────────────────┐
                    │  eBPF VM + 验证器 + Map + Helper │
                    └───────────────┬─────────────────┘
                                    │
     ┌──────────────┬───────────────┼───────────────┬──────────────┐
     ▼              ▼               ▼               ▼              ▼
 kprobes       uprobes        Tracepoints         USDT      perf_event/PMC
 (内核动态)    (用户动态)      (内核静态)        (用户静态)    (硬件采样)
     │              │               │               │              │
     └──────────────┴─────── BCC / bpftrace 工具 ──┴──────────────┘
                                    │
                          聚合 map / 栈 ID → 用户态展示
                                    │
                          火焰图 / 直方图 / 文本流
```

---

## 8. HFT 读者 Takeaway

1. **内核聚合、用户展示** — 热路径上只 export 统计，不 export 原始事件流。
2. **Tracepoint 优先，kprobe 兜底** — 内核升级维护成本差一个数量级。
3. **uprobe 远离高频函数** — `malloc`/每 tick 路径用 **采样** 或 **USDT**。
4. **火焰图要栈得先要有帧** — 构建链保留 frame pointer 或配 debuginfo。
5. **CO-RE 是跨内核部署的未来** — 定制工具长期应规划 libbpf + BTF。

---

## 相关章节

- 上一章：[chapter-01-简介.md](./chapter-01-简介.md)
- 下一章：[chapter-03-性能分析.md](./chapter-03-性能分析.md)
- BCC：[chapter-04-BCC.md](./chapter-04-BCC.md) · bpftrace：[chapter-05-bpftrace.md](./chapter-05-bpftrace.md)
- CPU / PMC 实践：[chapter-06-CPU.md](./chapter-06-CPU.md)
- C / CO-RE：[appendix-D-C语言BPF.md](./appendix-D-C语言BPF.md)
