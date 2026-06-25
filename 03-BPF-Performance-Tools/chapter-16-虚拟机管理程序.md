# Ch 16 虚拟机管理程序 · Hypervisors

> **BPF Performance Tools** · Brendan Gregg · **跳过 ⚪**

> 本章定位：**硬件虚拟化（Xen/KVM）上的 BPF** — [Ch 15 容器](./chapter-15-容器.md) 是 OS 级隔离；本章是 **Guest VM ↔ Hypervisor** 边界。需分别从 **访客机 (Guest)** 与 **宿主机 (Host)** 两侧观测。  
> **HFT：** 生产 **tick 路径优先裸金属**；若跑在 **云 VM / 托管 KVM** 上，Guest 侧 **`cpustolen`** 与 Host 侧 **`kvmexits`** 可证 **底层争抢**；**AWS Nitro** 等架构需退回 Ch 6–10 **通用资源工具**。  
> **上一章：** [chapter-15-容器.md](./chapter-15-容器.md) · **下一章：** [chapter-17-其他BPF工具.md](./chapter-17-其他BPF工具.md)

---

## 1. Part II 收官：虚拟化在栈中的位置

```
裸金属 HFT（首选）
    ↓ 若上云/VM
Guest OS + 本章 Guest 工具（cpustolen、xenhyper…）
    ↓
Hypervisor / KVM（Host：kvmexits）
    ↓
物理 CPU / NIC / 盘
```

**与容器对比：**

| | Ch 15 容器 | Ch 16 VM |
|---|------------|----------|
| 隔离 | namespaces + cgroups | **硬件虚拟化** |
| 典型争用 | cgroup throttle | **CPU stolen、VM exit** |
| BPF 跑哪 |  mostly **Host** | **Guest 与 Host 均可** |

---

## 2. 硬件虚拟化基础

### Hypervisor 配置

| 类型 | 例子 | 结构 |
|------|------|------|
| **裸金属 / Type-1** | **Xen** | Hypervisor 直接在硬件上，管理 Guest |
| **托管型 / Type-2 模块** | **KVM** | Linux 内核 **kvm 模块** + QEMU 等 |

Guest 内仍是 **完整 Linux 内核** — 故 **Ch 6–14 的 BPF 工具可在 Guest 内直接运行**（与物理机类似，但指标含虚拟化开销）。

### AWS Nitro 等演进

| 特点 | 分析含义 |
|------|----------|
| 网络/存储 **卸载到 Nitro 卡** | 少传统 KVM 设备模拟路径 |
| Hypervisor 功能 **硬件化** | **专用 Xen/KVM 工具减少** |
| 性能分析 | 更多依赖 **通用** `runqlat`、`tcpretrans`、`biolatency`（Ch 6–10） |

**HFT 上云：** 先 **`cpustolen` / 云监控 CPU credit** — 再决定是否值得深挖 `kvmexits`。

---

## 3. 分析策略：Guest vs Host

### 访客机 (Guest) 策略

| 检查项 | 工具/指标 |
|--------|-----------|
| **Hypercall 过多**（Xen PV） | `xen:xen_mc_*` tracepoint、`xenhyper` |
| **CPU 被偷取** | **`cpustolen`**、`%st`（top/mpstat） |
| 虚拟资源性能 | Ch 6–10 全套 — 结果 **含宿主机争抢** |

**解读 stolen time：** Guest 认为有 vCPU，但 **物理 CPU 被分给别的 Guest/Host** — P99 抖动 **与业务无关** 的常见根因。

### 宿主机 (Host) 策略

| 检查项 | 工具/指标 |
|--------|-----------|
| **VM exit** 频率与原因 | **`kvmexits`**、`perf kvm:*` |
| I/O 代理负载 | **QEMU** 进程 CPU、`biotop` |
| 物理资源 | Host 上 Ch 6–10 + **noisy VM** |

**原则：** Guest 内看到慢 → 先在 Guest **`cpustolen`**；仍可疑 → Host **`kvmexits`**。

---

## 4. 传统分析工具

Hypervisor **专用** 传统工具不多。

### KVM + perf（Host）

```bash
perf stat -e 'kvm:*' -a sleep 10
perf record -e kvm:kvm_exit -a sleep 10
perf script
```

| 事件 | 含义 |
|------|------|
| **VM exit** | Guest 操作需 Hypervisor 处理 |
| 退出原因 | HLT、IO、MSR、EPT violation… |

→ 与 **`kvmexits`** bpftrace 互补 — perf 更通用，bpftrace 更易 **直方图按原因分桶**。

### Guest 侧传统指标

| 来源 | 字段 |
|------|------|
| `top` / `mpstat` | **`%st` (steal)** |
| `/proc/stat` | `steal` jiffies |

---

## 5. Guest BPF 工具

### Xen Hypercalls（半虚拟化 PV）

追踪 **`xen:xen_mc_*`** tracepoints — 批量/单次 **hypercall** 计数与延迟。

### `xenhyper`（bpftrace）

通过 **`xen_mc_entry`** 统计具体 hypercall 类型：

| 类型（示例） | 含义 |
|--------------|------|
| `mmu_update` | 页表更新 |
| `stack_switch` | 栈切换 |
| … | 见工具输出 |

```bash
# 工具名以发行版 man 为准
sudo xenhyper.bt   # 或 bpftrace 脚本 xenhyper
```

**适用：** **Xen PV Guest** — 现代云多为 **HVM/PVH**，hypercall 分析范围变窄。

### Xen Callbacks（Host → Guest）

Xen 向 Guest **回调**（如 **IRQ / evtchn upcall**）— 追踪 **`xen_evtchn_do_upcall()`** 等，定位 **哪类进程被注入中断**。

### `cpustolen` — Stolen CPU 时间 🔴

Guest 内 **CPU 被偷取时间** 的 **延迟直方图**。

```bash
sudo cpustolen-bpfcc 10
# 或 bpftrace 版 cpustolen(8)
```

| 直方图 | 含义 |
|--------|------|
| 右尾长 | **宿主机过度订阅 (oversubscription)** — 与其他 VM 抢物理 CPU |
| 接近 0 | Guest vCPU **基本独占** 物理核（或 steal 未计量场景） |

**HFT：** 云 VM 上 P99 无法压下去 → **先看 stolen**；高 stolen → **换 dedicated host / 裸金属**，而非调策略代码。

### HVM Guest 注意

**全虚拟化 (HVM)** hypercall 路径少 — 延迟推断靠 **Ch 6–13 常规工具** + **`cpustolen`/`%st`**。

---

## 6. Host BPF 工具

### `kvmexits` — VM Exit 直方图 🔴

Host 上 bpftrace 工具：**VM exit 耗时分布** + **退出原因**。

```bash
sudo kvmexits.bt   # 或发行版包装脚本
```

| 退出原因（示例） | 常见解读 |
|------------------|----------|
| **`HLT`** | vCPU **空闲 halt** — 通常正常、耗时可长 |
| **`EXTERNAL_INTERRUPT`** | 外部中断注入 Guest |
| **`MSR_WRITE` / `MSR_READ`** | 模型特定寄存器访问 |
| **`EPT_VIOLATION`** | 嵌套页表 miss — MMIO/内存模拟 |
| **`IO_INSTRUCTION`** | 端口 I/O 模拟 — 设备路径慢 |

**价值：** Host 管理员 **快速定位异常 exit** — 某原因延迟尖刺 → 查 KVM/QEMU/设备模拟。

### Host 分析 Guest 的局限（Future Work）

| 能做 | 难做 |
|------|------|
| 获取 **Guest RIP**（退出时指令指针） | **无 Guest 符号表** → 难译成函数名 |
| 统计 exit 原因与延迟 | **进程级** 上下文在 Guest 内 |

**结论：** **深度应用/profile 仍在 Guest 内**；Host 侧 **`kvmexits`** 看 **虚拟化层** 健康度。

---

## 7. 工具选型速查

| 场景 | 视角 | 工具 |
|------|------|------|
| 云 VM 延迟抖 | Guest | **`cpustolen`**、`%st` |
| Xen PV hypercall 多 | Guest | `xenhyper`、xen tracepoints |
| 宿主机 VM 争抢 | Host | **`kvmexits`**、perf `kvm:*` |
| QEMU 吃 CPU | Host | `profile` on qemu |
| Nitro/现代云 | Both | Ch 6–10 通用工具 |
| 与容器混部 | — | [Ch 15](./chapter-15-容器.md) + 本章 Host |

---

## 8. Part II 总结

| 章 | 环境 |
|----|------|
| 6–10 | 资源（CPU/内存/FS/网/盘） |
| 11–12 | 安全 / 语言 |
| 13 | 应用 |
| 14 | 内核 |
| 15 | **容器** |
| 16 | **VM** |

**HFT 路径：** 能裸金属则 **不读 15–16**；上云则 **16 Guest `cpustolen` 必知**。

---

## 9. HFT 读者 Takeaway

1. **⚪ 默认跳过** — 裸金属为主；**云 VM / 托管 KVM** 时本章 **选读**。
2. **`cpustolen` / `%st`** — 「代码没问题但 P99 抖」的第一层 **基础设施证伪**。
3. **`kvmexits`（Host）** — 运维/平台团队查 **oversubscription、异常 exit**。
4. **Nitro 类架构** — 少依赖 Xen 专用工具；**通用 BPF + 云厂商指标**。
5. **Guest 内仍可跑 Ch 3 清单** — 但解读时记得 **结果含虚拟化 tax**。
6. **深度栈分析在 Guest** — Host 只有 exit 原因与 RIP，无 Guest 符号。
7. 后续 **Part III**：生态工具 [Ch 17](./chapter-17-其他BPF工具.md)、避坑 [Ch 18](./chapter-18-技巧与常见问题.md)。

---

## 相关章节

- 上一章：[chapter-15-容器.md](./chapter-15-容器.md)
- 下一章：[chapter-17-其他BPF工具.md](./chapter-17-其他BPF工具.md)
- CPU stolen / runqlat：[chapter-06-CPU.md](./chapter-06-CPU.md)
- 云/虚拟化：[chapter-11-cloud-computing](../02-Systems-Performance-2nd/chapter-11-cloud-computing/)（若存在）
- Hennessy 虚拟化：[04-Computer-Architecture-6th](../04-Computer-Architecture-6th/)
