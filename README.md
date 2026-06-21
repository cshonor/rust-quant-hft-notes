# rust-quant-hft-handbook

本仓库收录 **Rust 全栈量化** + **HFT 微秒级低延迟** 学习笔记，配套原理拆解、可运行源码与工程实践。

**技术板块已封顶（`00`–`12`）** — 不再新增顶层编号文件夹；剩余工作为各目录内笔记、代码实验与跨模块联动。

→ 板块边界与对照逻辑：[CROSS-MODULE-GUIDE.md](./CROSS-MODULE-GUIDE.md)  
→ **进阶主叙事（分享/复习用）：[LEARNING-CHAIN.md](./LEARNING-CHAIN.md)** ← 建议收藏

---

## 🔗 学习链路 · L1→L5（一眼版）

> **链路 L1–L5 ≠ 文件夹 `01`–`12`。** 文件夹序号是仓库归类；**学习顺序跟链路走。**

```
L0  00-Harris           业务锚点
L1  08-CSAPP (+07)      知其所以然 — 硬件与程序怎么跑
L2  01-SysPerf          知其然 — 性能分析方法论
L3  09-BPF              工具落地 — bpftrace/BCC 生产追踪
L4  02/03 + 网络栈      系统纵深 — 内核 / 内存 / 协议→DPDK
L5  10-HFT + 11-Rust    动手实现 — C++ / Rust 高性能工程
```

详解与各步铺垫关系 → **[LEARNING-CHAIN.md](./LEARNING-CHAIN.md)**

---

## 🗺️ HFT 阅读顺序（总纲）

> 小节级读/跳指引 → [HFT-READING-ROADMAP.md](./HFT-READING-ROADMAP.md) · 链路叙事 → [LEARNING-CHAIN.md](./LEARNING-CHAIN.md)

| 链路 | 读什么 | 目的 |
|------|--------|------|
| **L0** | [00-Trading-and-Exchanges](./00-Trading-and-Exchanges/) | 业务锚点 · LOB/市场结构 |
| **L1** | [08-CSAPP-3rd](./08-CSAPP-3rd/) 地基 + [07-Hennessy](./07-Computer-Architecture-6th/) Ch2 | **知其所以然** — Cache/进程/VM/锁 |
| **L2** | [01-Systems-Performance-2nd](./01-Systems-Performance-2nd/) | **知其然** — USE、延迟分解、perf |
| **L3** | [09-BPF-Performance-Tools](./09-BPF-Performance-Tools/) | **工具落地** — 紧接 L2，eBPF 生产观测 |
| **L4** | [02-LKD](./02-Linux-Kernel-Development/) → [03-Gorman](./03-Linux-Virtual-Memory-Manager/) → [04/05/06/12 网络](./CROSS-MODULE-GUIDE.md) | 系统纵深 · 绑核/NUMA/收包/DPDK |
| **L5** | [10-HFT-Low-Latency-Practice](./10-HFT-Low-Latency-Practice/) + [11-Rust-Quant-Trading-Guide](./11-Rust-Quant-Trading-Guide/) | **动手实现** — C++/Rust 量化工程 |

**执行序号：** L0 → L1 → L2 → L3 → L4 → L5（L4 中 CSAPP 网络章 Ch10–11 与 UNP/Rosen 合读）

| 标签 | 含义 |
|------|------|
| 🔴 **必读** | HFT 热路径，不能 skip |
| 🟡 **选读** | 后补或场景触发（如订单走 TCP） |
| ⚪ **跳过** | 本仓库无笔记，默认不读 |

---

## 📚 仓库目录（`00`–`12` = 全部技术板块）

| 序号 | 文件夹 | 板块 | 内容 |
|------|--------|------|------|
| 00 | [00-Trading-and-Exchanges](./00-Trading-and-Exchanges/) | 交易理论 | Harris · 市场/LOB（29 章） |
| 01 | [01-Systems-Performance-2nd](./01-Systems-Performance-2nd/) | Linux 系统 | Gregg · 性能方法论 |
| 02 | [02-Linux-Kernel-Development](./02-Linux-Kernel-Development/) | Linux 系统 | Love · LKD 3rd + 3 门前置课 [LEARNING-PATH](./02-Linux-Kernel-Development/LEARNING-PATH.md) |
| 03 | [03-Linux-Virtual-Memory-Manager](./03-Linux-Virtual-Memory-Manager/) | Linux 系统 | Gorman · 14 章 + 附录 [OUTLINE](./03-Linux-Virtual-Memory-Manager/OUTLINE.md) |
| 04 | [04-TCP-IP-Illustrated-Vol1](./04-TCP-IP-Illustrated-Vol1/) | **网络** | Stevens · 协议原理 → [外部仓库](https://github.com/cshonor/Computer-Networking) |
| 05 | [05-UNP-Vol1](./05-UNP-Vol1/) | **网络** | Stevens · Socket API → [外部仓库](https://github.com/cshonor/Computer-Networking) |
| 06 | [06-Linux-Kernel-Networking](./06-Linux-Kernel-Networking/) | **网络** | Rosen · 14 章 + 附录 [OUTLINE](./06-Linux-Kernel-Networking/OUTLINE.md) |
| 07 | [07-Computer-Architecture-6th](./07-Computer-Architecture-6th/) | 硬件 CPU | Hennessy · 7 章 + 附录 [OUTLINE](./07-Computer-Architecture-6th/OUTLINE.md) |
| 08 | [08-CSAPP-3rd](./08-CSAPP-3rd/) | 硬件 CPU | CSAPP · 12 章 + 附录 + Lab |
| 09 | [09-BPF-Performance-Tools](./09-BPF-Performance-Tools/) | 性能观测 | Gregg · 18 章 + 附录 [OUTLINE](./09-BPF-Performance-Tools/OUTLINE.md) |
| 10 | [10-HFT-Low-Latency-Practice](./10-HFT-Low-Latency-Practice/) | **工程落地** | 整机调优 / 对接 / 架构 / 压测（≠ 网络书） |
| 11 | [11-Rust-Quant-Trading-Guide](./11-Rust-Quant-Trading-Guide/) | Rust 开发 | 量化工程 · 无锁 |
| 12 | [12-DPDK-Low-Latency-Network](./12-DPDK-Low-Latency-Network/) | **网络** | DPDK 用户态旁路 · **网络栈闭环** |

每本书文件夹内 **README.md** = 必读/选读/跳过速查。

书目裁剪与映射表 → [READING-LIST.md](./READING-LIST.md)

---

## 🛠️ 技术栈

- 主力语言：Rust
- 核心库：RustQuant、Barter-rs、Tokio、io_uring
- 学习辅助：NotebookLM 书籍提炼 + Cursor 代码辅助

## 📌 仓库维护规范

- 根目录文件夹以 **`00-` ~ `12-` 序号前缀** 排序；**编号封顶，不再扩展顶层目录**
- 章节按序号独立拆分，单文件单一主题
- 笔记、源码、配图严格分区（`code/`、`assets/`）
- 外部书目只建索引 README，不 duplicate 另一仓库的全文笔记
- 跨模块对照统一维护在 [CROSS-MODULE-GUIDE.md](./CROSS-MODULE-GUIDE.md)
