# rust-quant-hft-handbook

本仓库收录 **Rust 全栈量化** + **HFT 微秒级低延迟** 学习笔记，配套原理拆解、可运行源码与工程实践。

**技术板块 `00`–`17` + 嵌入式 Linux 支线 `18`–`23`** — **文件夹编号 = HFT 主线推荐阅读顺序**（见下与 [LEARNING-CHAIN.md](./LEARNING-CHAIN.md)）。

→ 一眼进阶路径：[LEARNING-CHAIN.md](./LEARNING-CHAIN.md)  
→ 板块对照：[CROSS-MODULE-GUIDE.md](./CROSS-MODULE-GUIDE.md)

---

## 🗺️ HFT 主线阅读顺序（= 文件夹编号）

```
00 业务 → 01 CSAPP → 02 Hennessy
→ 03 LKD → 04 ULK → 05 Gorman → 06 TLPI
→ 07 MikanOS/30天OS → **08 C++** → 09 陈硕 PNP/muduo → 10 UNP
→ 11 TCP/IP → 12 Rosen → 13 DPDK
→ 14 SysPerf → 15 BPF
→ 16 HFT 工程 → 17 Rust 量化
```

**可选支线 · 嵌入式 Linux + 飞控算法（ARM-A，非 MCU）：** `18 → … → 23`（建议 03–06 后再开 · **23 用业余时间**）→ [路线图 §六](./HFT-READING-ROADMAP.md#六嵌入式-linux-支线18–23)

| 文件夹 | 模块 |
|:------:|------|
| **00** | [Trading and Exchanges](./00-Trading-and-Exchanges/) — Harris · LOB（练手：[00-practice-go-dex](./00-Trading-and-Exchanges/00-practice-go-dex/)） |
| **01** | [CSAPP-3rd](./01-CSAPP-3rd/) — 知其所以然 · 程序与硬件 |
| **02** | [Computer-Architecture-6th](./02-Computer-Architecture-6th/) — Hennessy · 体系结构（紧接 01） |
| **03** | [Linux-Kernel-Development](./03-Linux-Kernel-Development/) — LKD |
| **04** | [Understanding-Linux-Kernel](./04-Understanding-Linux-Kernel/) — ULK（紧接 03） |
| **05** | [Linux-Virtual-Memory-Manager](./05-Linux-Virtual-Memory-Manager/) — Gorman |
| **06** | [The-Linux-Programming-Interface](./06-The-Linux-Programming-Interface/) — TLPI |
| **07** | [system-low-level-hands-on](./07-system-low-level-hands-on/) — **01 MikanOS** / 02 30天 OS |
| **08** | [cpp-learning-notes](./08-cpp-learning-notes/) — C++ · [GitHub 笔记仓](https://github.com/cshonor/cpp-learning-notes) |
| **09** | [Practical-Network-Programming](./09-Practical-Network-Programming/) — PNP / muduo |
| **10** | [UNP-Vol1](./10-UNP-Vol1/) |
| **11** | [TCP-IP-Illustrated-Vol1](./11-TCP-IP-Illustrated-Vol1/) |
| **12** | [Linux-Kernel-Networking](./12-Linux-Kernel-Networking/) — Rosen |
| **13** | [DPDK-Low-Latency-Network](./13-DPDK-Low-Latency-Network/) |
| **14** | [Systems-Performance-2nd](./14-Systems-Performance-2nd/) — Gregg · 性能方法论 |
| **15** | [BPF-Performance-Tools](./15-BPF-Performance-Tools/) — eBPF（紧接 14） |
| **16** | [HFT-Low-Latency-Practice](./16-HFT-Low-Latency-Practice/) — 原书 Ch1–11 已映射 · Ch13 策略 / Ch14 Python 扩展 |
| **17** | [Rust-Quant-Trading-Guide](./17-Rust-Quant-Trading-Guide/) |
| **18** | [ARM64-Architecture](./18-ARM64-Architecture/) — ARMv8-A · 对照 x86 |
| **19** | [UBoot-Kernel-Build](./19-UBoot-Kernel-Build/) — U-Boot · 内核裁剪 · Buildroot |
| **20** | [Linux-Device-Driver](./20-Linux-Device-Driver/) — LDD · 内核态驱动 |
| **21** | [Device-Tree-Study](./21-Device-Tree-Study/) — 设备树 |
| **22** | [Embedded-Linux-Practice](./22-Embedded-Linux-Practice/) — 无人机 / 网关实战 |
| **23** | [Motion-Control-Motor](./23-Motion-Control-Motor/) — PID · IMU · 电机 · 飞控（非 MCU） |

> **内核段：** `03`–`07` → **`08` C++** → 网络 `09`–`13` → 性能 `14`–`15` → 工程 `16`–`17`。  
> **嵌入式退路：** `18`–`23` 与 HFT **并行或后置** — 飞行器 / 网关 / **飞控算法**。

---

## 🎯 研究方向（GitHub 简介）

**English**

> My primary research interest lies in HFT quantitative-trading backend development. As a long-term secondary path, I also learn embedded Linux on the ARM-A platform. I implement self-coded PID control algorithms, motor-driver programming, IMU-sensor communication and flight-control scheduling logic, avoiding STM32-M4 bare-metal development, to build a self-developed drone project as an alternative-career track.

**中文**

> 核心主攻方向为高频量化（HFT）后端开发；同时拓展 ARM-A 平台下的嵌入式 Linux，自研实现 PID 控制算法、电机驱动、IMU 传感器通信与飞控调度逻辑，绕开 STM32-M4 单片机裸机开发，自研无人机项目，作为职业备选路线。

小节级读/跳 → [HFT-READING-ROADMAP.md](./HFT-READING-ROADMAP.md) · 书目裁剪 → [READING-LIST.md](./READING-LIST.md)

| 标签 | 含义 |
|------|------|
| 🔴 **必读** | HFT 热路径 |
| 🟡 **选读** | 后补或场景触发 |
| ⚪ **跳过** | 默认不读 |

---

## 🛠️ 技术栈

| 主线 | 语言 / 库 |
|------|-----------|
| **HFT / 网络** | C · C++（muduo/DPDK）· 低延迟工程 |
| **量化 / 备选** | Rust · RustQuant · Barter-rs · Tokio · io_uring |
| **嵌入式支线** | C · GNU-C · ARM64 Linux · 驱动 / DT · **PID / 飞控** |
| **学习辅助** | NotebookLM · Cursor |

## 📌 维护规范

- 顶层 **`00-` ~ `23-`**：`00`–`16` HFT 主线在本仓；**`17`** 为 [cpp-learning-notes](https://github.com/cshonor/cpp-learning-notes) **外部索引**；**`18`–`23`** 嵌入式 Linux + 运动控制支线（可选）
- 笔记 / 源码 / 配图分区（`code/`、`assets/`）
- 外部书目只建索引，不 duplicate 全文笔记
