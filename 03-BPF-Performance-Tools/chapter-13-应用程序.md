# Ch 13 应用程序 · Applications

> **BPF Performance Tools** · Brendan Gregg · **选读 🟡**

> 本章定位：**把资源消耗 ↔ 应用上下文绑在一起** — Ch 6–10 从 CPU/内存/FS/网看系统；本章从 **线程、锁、syscall、USDT** 看 **哪个业务路径** 在花钱。以 **MySQL** 为主案例，方法论可迁移到 **策略进程、网关、风控服务**。  
> **HFT：** **`profile` + `offcputime` + `syscount`** 是策略延迟三板斧；锁竞争看 **`pmlock`/`futex`**；共置 MySQL/Redis 用 **USDT/慢查询类工具** 作模板。注意 **libc 帧指针断裂** 坑。  
> **上一章：** [chapter-12-语言.md](./chapter-12-语言.md) · **下一章：** [chapter-14-内核.md](./chapter-14-内核.md)

---

## 1. 为什么需要应用层分析

| 仅看资源 | 遗漏 |
|----------|------|
| 磁盘 I/O 高 | **哪条 SQL / 哪个写日志路径** |
| CPU 高 | **哪个策略回调 / 哪个线程** |
| 网络重传 | **哪个进程 connect**（Ch 10 已部分覆盖） |

```
资源层（Ch 6–10）          应用层（本章）
biolatency / tcpretrans  +  SQL / 函数栈 / 锁名
        \                    /
         \   USDT / ustack   /
          -------------------
              完整故事
```

---

## 2. 应用程序基础 (Application Fundamentals)

### 线程管理 (Thread Management)

| 模式 | 说明 | HFT 常见 |
|------|------|----------|
| 每连接一线程 | 简单，扩展差 | 少见 |
| **线程池** | 固定 worker 处理任务 | 网关、IO |
| **事件驱动 / SEDA** | 单线程或分阶段 pipeline | **策略 hot path** |
| 绑核 | 减少迁移 | `taskset` / isolcpus |

**BPF 关联：** `threadsnoop` 看 **何时 `pthread_create`**；`threaded` 看 **是否仅一线程在跑**。

### 锁 (Locks)

`libpthread`：**mutex、rwlock、spinlock** — **锁竞争** → 线程阻塞 → Off-CPU 在 **futex**。

| 现象 | 工具线索 |
|------|----------|
| P99 抖、CPU 不高 | `offcputime` 栈含 `futex` / `pthread_mutex_lock` |
| 谁等谁 | **`pmlock` / `pmheld`** |

→ [15-HFT ch07 无锁](../15-HFT-Low-Latency-Practice/chapter-07-无锁数据结构与内存布局.md)

### 休眠 (Sleeps)

应用显式 **`sleep` / `nanosleep` / `usleep`** — 常为 **人为延迟** 或错误轮询。

| 工具 | 作用 |
|------|------|
| **`naptime`** | 追踪 `nanosleep(2)` — 抓 **代码里写死的 sleep** |

**HFT：** 热路径不应有 sleep；`naptime` 一击即中。

---

## 3. 应用程序上下文与 USDT

**最可靠** 获取业务语义（SQL、ORM 操作、自定义事件）→ **USDT**。

### MySQL 示例

编译 **`-DENABLE_DTRACE=1`** 时提供 USDT，例如：

| 探针（示意） | 暴露 |
|--------------|------|
| `mysql:query__start` | 当前 **SQL** |
| `mysql:command__start` | 命令类型 |

```bash
# 列出 USDT（若已启用）
bpftrace -l 'usdt:/usr/sbin/mysqld:*'
```

**HFT：** 共置 **MySQL/ MariaDB** 审计慢查询；自研引擎可 **自建 USDT**（Ch 12 编译型思路）。

**原则：** USDT > 高频 uprobe；见 [Ch 2 § USDT](./chapter-02-技术背景.md)、[Ch 12](./chapter-12-语言.md)。

---

## 4. 进程与线程分析

### `execsnoop`

后台频繁 **短生命周期子进程**（shell 脚本）— 极低效。

→ [Ch 6](./chapter-06-CPU.md) · [Ch 11 安全](./chapter-11-安全.md)

```bash
sudo execsnoop-bpfcc
```

### `threadsnoop`

追踪 **`pthread_create()`** — 线程池何时扩容、入口函数。

```bash
sudo threadsnoop-bpfcc -p $(pidof myapp)
```

### `threaded`

采样 **哪些线程在 CPU 上跑** — 验证 **负载均衡**（是否单线程 100%、其余闲置）。

```bash
sudo threaded-bpfcc -p $(pidof myapp) 10
```

**HFT：** 多线程策略若 **`threaded` 显示一核独忙** — 并行度或绑核配置错误。

---

## 5. CPU 与 Off-CPU 剖析（核心）

### `profile` — On-CPU 火焰图

```bash
sudo profile-bpfcc -F 99 -p $(pidof my_strategy) 30
```

找出 **最耗 CPU 的应用代码路径** — 需 [Ch 12 帧指针 + 符号](./chapter-12-语言.md)。

→ [Ch 6 § profile](./chapter-06-CPU.md)

### `offcputime` / `offcpuhist` — Off-CPU 火焰图 🔴

**应用延迟神器** — 线程 **为何离开 CPU**（锁、I/O、sleep）。

```bash
sudo offcputime-bpfcc -p $(pidof my_strategy) 30
sudo offcpuhist-bpfcc -p $(pidof myapp) 10   # 直方图形态
```

| Off-CPU 栈顶 | 常见原因 |
|--------------|----------|
| `futex` / `pthread_mutex_*` | **锁竞争** |
| `read` / `write` / `recv` | I/O / 网络 |
| `nanosleep` | 人为 sleep |
| `epoll_wait` | 正常等事件（看 wait 时长） |

**HFT runbook：** P99 升 + CPU 不忙 → **先 `offcputime`**，再决定查网/盘/锁。

---

## 6. 系统调用与 I/O

### `syscount`

按进程统计 **syscall 类型与次数**。

```bash
sudo syscount-bpfcc -p $(pidof my_strategy) 1
```

| 异常信号 | 可能问题 |
|----------|----------|
| 海量 **`futex`** | 锁竞争 |
| 海量 **`sched_yield`** | 错误让出 CPU /  spin 退化 |
| 海量 **`read`/`write`** | 意外同步 I/O |

→ [Ch 6 § syscount](./chapter-06-CPU.md)

### `ioprofile`

追踪 **I/O 相关 syscall**（读/写/send/recv）+ **用户态栈** — 哪段 **应用代码** 发起多余 I/O。

```bash
sudo ioprofile-bpfcc -p $(pidof myapp) 10
```

**注意：** 受 **libc 帧指针** 问题影响（见 §9）。

---

## 7. MySQL 专用工具（案例）

### `mysqld_qslower`

内核侧过滤 **慢于阈值** 的查询 — 比慢查询日志 **低开销**，直接打印 **SQL 字符串**。

```bash
sudo mysqld_qslower-bpfcc 10   # 10ms 阈值示例
```

### `mysqld_clat`

按 **命令类型**（`COM_QUERY`、`COM_STMT_EXECUTE`…）的 **延迟直方图**。

```bash
sudo mysqld_clat-bpfcc 10
```

**迁移思路：** 任何带 USDT 的服务（Postgres、自研引擎）→ **慢路径 BPF 过滤 + 业务字段打印**。

---

## 8. 锁与休眠排障

### `pmlock` / `pmheld`

针对 **`libpthread` mutex**：

| 工具 | 回答 |
|------|------|
| **`pmlock`** | **锁竞争** 栈 + 等待延迟 |
| **`pmheld`** | **谁持有锁** + 持有时长 |

```bash
sudo pmlock-bpfcc -p $(pidof myapp) 10
sudo pmheld-bpfcc -p $(pidof myapp) 10
```

**HFT：** 共置服务争用 **同一把全局 mutex** 时极有用；策略热路径应 **无 pmlock 热点**。

### `naptime`

追踪 **`nanosleep(2)`** — 揪出代码中的 **显式休眠**。

```bash
sudo naptime-bpfcc -p $(pidof myapp)
```

---

## 9. 信号 (Signals)

### `signals` / `killsnoop`

| 工具 | 作用 |
|------|------|
| `signals` | 追踪 **信号发送**（谁向谁发了什么） |
| `killsnoop` | 追踪 **kill** — 谁发了 **SIGKILL/SIGTERM** |

```bash
sudo killsnoop-bpfcc
```

**场景：** 策略进程 **意外退出** — OOM？人为 kill？watchdog？

---

## 10. 关键避坑：libc 帧指针断裂 ⚠️

**书中强调的现实：** 多数发行版 **`libc` / `libpthread` 编译时 omit frame pointer**。

| 后果 | 表现 |
|------|------|
| `offcputime` / `ioprofile` 从内核栈 **向上 walk** | 在 **libc 层断裂** |
| 只见 | `__pwrite+79`、`read+0x…` |
| 看不见 | **应用内部** 真实调用栈 |

**对策：**

| 方案 | 说明 |
|------|------|
| **应用 `-fno-omit-frame-pointer`** | 策略二进制必须（[Ch 12](./chapter-12-语言.md)） |
| 自编译 **带 FP 的 libc** | 极端，运维成本高 |
| **ORC / LBR** 等栈 walk | 内核/perf 能力，环境相关 |
| **在应用函数上 uprobe/USDT** | 跳过 libc，直接挂业务符号 |

**HFT 构建要求：** 策略 **.so/.exe 保留 FP + debuginfo**；否则 Off-CPU 火焰图 **半盲** — 与 SysPerf 应用章同训。

→ [SysPerf Ch 5 Applications](../02-Systems-Performance-2nd/chapter-05-applications/)

---

## 11. 应用分析工作流

```
1. 业务指标（P99、QPS）锁定 PID / 时间窗
2. syscount 10s        → futex? sched_yield? read?
3. profile 30s         → On-CPU 热点函数
4. offcputime 30s      → Off-CPU 等锁/I/O/sleep?
5. 资源章交叉验证
      futex 多 → pmlock/pmheld
      read 多 → ioprofile + Ch 8/9
      recv 多 → Ch 10 tcpretrans
6. 有 USDT → mysqld_qslower 类慢路径工具
7. naptime → 排除人为 sleep
```

---

## 12. HFT 读者 Takeaway

1. **资源 + 应用上下文** 才完整 — 「磁盘忙」要追到 **哪段代码 write**（`ioprofile`/`biostacks` Ch 9）。
2. **延迟三板斧：** `profile`（在算）+ **`offcputime`（在等）** + `syscount`（在 syscall 什么）。
3. **锁：** `syscount` 见 `futex` → **`pmlock`**；热路径应用层应 **无锁/细粒度**（15-HFT ch07）。
4. **`naptime`** — 低 hanging fruit；策略代码禁止 sleep 轮询。
5. **MySQL 工具** — 共置 DB 的模板；自研服务学 **USDT + 内核侧慢过滤**。
6. **libc 帧指针** — 不解决则 Off-CPU 图 **停在 libc**；发布链 **-fno-omit-frame-pointer** 非可选。
7. **短窗口、限 PID** — 与全书生产纪律一致。

---

## 相关章节

- 上一章：[chapter-12-语言.md](./chapter-12-语言.md)
- 下一章：[chapter-14-内核.md](./chapter-14-内核.md)
- CPU profile/offcpu：[chapter-06-CPU.md](./chapter-06-CPU.md)
- 语言/符号：[chapter-02-技术背景.md](./chapter-02-技术背景.md)
- SysPerf 应用：[chapter-05-applications](../02-Systems-Performance-2nd/chapter-05-applications/)
- HFT 无锁：[chapter-07-无锁数据结构与内存布局](../15-HFT-Low-Latency-Practice/chapter-07-无锁数据结构与内存布局.md)
- CSAPP 并发：[chapter-12-concurrent-programming](../01-CSAPP-3rd/chapter-12-concurrent-programming/)
