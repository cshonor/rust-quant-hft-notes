# Ch 1 简介 · Introduction

> **BPF Performance Tools** · Brendan Gregg · **精读 🔴**

> 本章定位：**全书导论** — 术语、工具链第一印象、两个「现场排障」故事，以及 BPF 相对传统观测的 **可见性** 与 **插桩** 分类。技术细节在 [Ch 2](./chapter-02-技术背景.md)；BCC / bpftrace 专章见 [Ch 4](./chapter-04-BCC.md) · [Ch 5](./chapter-05-bpftrace.md)。  
> **HFT：** 生产裸机把 **BCC 预制工具 + bpftrace 即兴脚本** 当作与 `perf` 并列的标配 — 本章建立「该用哪条链、能解决什么盲区」的地图。  
> **SysPerf 对照：** [02-SysPerf Ch 15 BCC/bpftrace](../02-Systems-Performance-2nd/chapter-15-bpf/) · [Ch 4 观测工具](../02-Systems-Performance-2nd/chapter-04-observability-tools/)

---

## 1. 基础概念

| 术语 | 含义 |
|------|------|
| **BPF** | 经典 Berkeley Packet Filter — 最初用于 tcpdump 包过滤的 **内核字节码 VM** |
| **eBPF** | 扩展 BPF（2014+）— **通用、图灵完备、可验证** 的内核沙箱程序；本书「BPF」多指此 |
| **Tracing** | **事件追踪** — 每次事件发生记录一条（exec、open、syscall enter/exit） |
| **Snooping** | **嗅探** — 非修改地观察活动（opensnoop、execsnoop 一类） |
| **Sampling** | **采样** — 周期性快照（如 `profile` 按频率采栈）；低开销、可能漏短事件 |
| **Profiling** | **剖析** — 汇总「时间/次数花在哪」；常与采样栈或聚合 map 结合 |
| **Observability** | **可观测性** — 从外部输出推断内部状态；BPF 让 **内核 + 用户态** 同屏可见 |

> **HFT 直觉：** 延迟尖刺往往是 **短事件**（一次 block I/O、一次 run-queue 排队、一次 TCP 重传）— **Tracing/BCC 直方图** 补 **perf 采样** 的盲区；采样适合 CPU 热点，追踪适合「谁、何时、持续了多久」。

---

## 2. 核心前端：为何需要 BCC / bpftrace

直接写 **内核 BPF 字节码** 极其繁琐。本书聚焦高级前端：

| 前端 | 角色 | 典型用法 |
|------|------|----------|
| **BCC** | Python/Lua/C 框架 + **成套预制工具** | `execsnoop`、`biolatency`、`runqlat` — 日常 runbook |
| **bpftrace** | 类 awk 的 **单行/短脚本语言** | 即兴 kprobe、tracepoint、USDT — ad hoc 根因 |
| **IO Visor** | 早期 eBPF 商业化/教育项目（BCC 生态背景） | 理解历史；生产以 **bcc-tools + bpftrace** 为主 |

→ 深入：[chapter-04-BCC.md](./chapter-04-BCC.md) · [chapter-05-bpftrace.md](./chapter-05-bpftrace.md)

---

## 3. BCC 工具初探 · 快速排障

### execsnoop — 谁在疯狂拉起进程？

```bash
sudo execsnoop-bpfcc    # 或 execsnoop，视发行版包名
```

**场景：** 后台服务每秒尝试启动却失败 — 传统日志可能无记录，**exec 事件** 在 BPF 里一览无余（父进程、命令行、返回值）。

**HFT：** 异常 watchdog、僵尸 helper、错误 cron — 排查 **非策略进程** 干扰 CPU cache / 磁盘。

### biolatency — 磁盘 I/O 延迟分布

```bash
sudo biolatency-bpfcc -F -m 5 10
```

**输出：** 块 I/O **延迟直方图**（毫秒桶），10 秒窗口。

**场景：** 「磁盘慢」不能只看平均 — **长尾桶**（如 >32 ms）暴露 journal、日志盘、误配 NFS 等问题。

**HFT：** 共置裸机若出现块设备延迟，常是 **日志/监控/agent** — 与 [SysPerf Ch 9 磁盘](../02-Systems-Performance-2nd/chapter-09-disks/) 的 USE + 直方图方法论一致。

---

## 4. BPF 的可见性 (Visibility)

| 传统工具局限 | BPF 能做什么 |
|--------------|--------------|
| 固定统计项、盲区多 | **可编程** — 按需 hook 任意内核/用户路径 |
| 改配置常需重启或特殊模式 | **生产在线** attach/detach，验证器保证安全 |
| 用户态只见 syscall 入口 | **内核栈、TCP 内部、块层、调度器** 同一工具链 |

Gregg 的比喻：**X 射线** — 穿透整栈，而非只看 `/proc` 或应用日志。

**HFT：** 策略热路径在 user space，但 **run queue、重传、direct reclaim、off-CPU** 都在内核 — BPF 把「延迟在栈外哪一段」钉死。

---

## 5. 动态插桩 vs 静态插桩

| 类型 | 机制 | 特点 |
|------|------|------|
| **动态 · kprobes** | 内核函数入口/偏移 hook | 灵活；函数名随内核版本可能变 |
| **动态 · uprobes** | 用户态二进制/库函数 hook | 需符号；可追自定义 SO |
| **静态 · Tracepoints** | 内核 **稳定** 插桩点 | ABI 稳定，首选内核事件 |
| **静态 · USDT** | 用户态 **静态定义** 探针（如 Python、MySQL、部分 C++） | 需编译时 `-fno-omit-frame-pointer` 等；零开销未启用时 |

> **不用时零开销（动态）：** probe **未 attach** 则无成本；attach 后成本取决于 **频率 ×  per-event 逻辑** — HFT 热路径上只开 **聚合 map**，避免 per-event 打印。

→ 架构细节：[chapter-02-技术背景.md](./chapter-02-技术背景.md)

---

## 6. bpftrace 与 BCC 演示 · 追 `open()`

### bpftrace — 单行

```bash
sudo bpftrace -e 'tracepoint:syscalls:sys_enter_openat { printf("%s %s\n", comm, str(args->filename)); }'
```

**特点：** 语法短，适合 **5 分钟验证假设**。

### BCC — opensnoop

```bash
sudo opensnoop-bpfcc
```

**特点：** 列格式化输出、过滤、错误码 — **可脚本化、可给 SRE runbook**。

**共同目标：** 捕获 **文件打开** — 查配置读失败、权限、错误路径（「软件行为异常但无 crash」类问题）。

**HFT：** 查策略是否误读大文件、NFS 配置、证书路径 — 与 strace 相比 **生产开销更可控**。

---

## 7. HFT 读者 Takeaway

1. **BPF ≠ 只做网络过滤** — eBPF 是 **内核可编程观测 +（另册）XDP/tc 数据面**。
2. **先 BCC 标准工具，再 bpftrace 定制** — 与 [SysPerf 15.1.7](../02-Systems-Performance-2nd/chapter-15-bpf/notes/section-15.1.7-BCC-vs-bpftrace.md) 一致。
3. **Tracing 补 Sampling** — `profile` 找 CPU 热点；`runqlat` / `biolatency` / `tcpretrans` 找 **延迟与长尾**。
4. **Tracepoint > kprobe**（能用时）— 内核升级时脚本更稳。

---

## 相关章节

- 下一章：[chapter-02-技术背景.md](./chapter-02-技术背景.md)
- BCC 专章：[chapter-04-BCC.md](./chapter-04-BCC.md)
- bpftrace 专章：[chapter-05-bpftrace.md](./chapter-05-bpftrace.md)
- 附录 A 单行命令：[appendix-A-bpftrace单行命令.md](./appendix-A-bpftrace单行命令.md)
