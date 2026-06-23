# HFT 学习链路 · 从知其所以然到动手实现

> **文件夹 `00`–`15`。** **执行序号**见文末。

```
知其所以然  →  知其然  →  工具落地  →  系统纵深  →  网络实战  →  工程实现
  01–04         02          03          05–08         09–13           14–15
```

---

## 一眼版 · 推荐执行顺序

```
00  Harris
01  CSAPP + 04 Hennessy
02  SysPerf → 03  BPF
05  LKD → 06  Gorman

07  TLPI                 ← Linux 用户态：epoll / mmap / 线程
08  自制 OS / CPU
09  陈硕 PNP / muduo
10  UNP
01  CSAPP Ch10–11
11  TCP/IP → 12  Rosen → 13  DPDK

14  HFT Practice
15  Rust Guide
```

**最短四步：** `01` → `02` → `03` → `14`/`15`

---

## 文件夹 ↔ 阶段

| 文件夹 | 模块 | 阶段 |
|--------|------|------|
| **07** | [TLPI](./07-The-Linux-Programming-Interface/) | Linux 用户态 syscall |
| **08** | [自制 OS/CPU](./08-system-low-level-hands-on/) | 底层动手 |
| **09–13** | PNP / UNP / TCP/IP / Rosen / DPDK | 网络纵深 |
| **14–15** | HFT / Rust | 工程实现 |

---

## 07 · TLPI 在链上的位置

```
05 LKD（内核里是什么）  →  07 TLPI（用户态怎么调）
06 Gorman（VM 深度）    →  07 TLPI（mmap/mlock）
07 TLPI（epoll）        →  09 PNP（写网络服务）
07 TLPI（socket 基础）  →  10 UNP（API 系统化）
```

→ [OUTLINE.md](./07-The-Linux-Programming-Interface/OUTLINE.md)

---

## 相关文档

- [READING-LIST.md](./READING-LIST.md) · [HFT-READING-ROADMAP.md](./HFT-READING-ROADMAP.md) · [CROSS-MODULE-GUIDE.md](./CROSS-MODULE-GUIDE.md)

**执行序号：** `00 → 01(+04) → 02 → 03 → 05 → 06 → 07 → 08 → 09 → 10 → 01网络章 → 11 → 12 → 13 → 14 → 15`
