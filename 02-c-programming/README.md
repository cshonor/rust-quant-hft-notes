# 02 · C 语言 · 系统级编程

**文件夹 `02`** · [LEARNING-CHAIN](../LEARNING-CHAIN.md)

> **定位：** **01 CSAPP 之后、03 Hennessy 之前** — 把「机器/程序长什么样」落成 **能写对的 C**。  
> **主线：** HFT / 内核 / MikanOS / DPDK 的 **共同语言**；**09 C++** 是后续加 RAII，不是跳过 C。

---

## 为什么卡在这里？

| 上游 | 本模块 | 下游 |
|------|--------|------|
| [01 CSAPP](../01-CSAPP-3rd/) 硬件 + 机器级程序 **整体图景** | **指针、内存、系统调用思维** 写熟 | [03 Hennessy](../03-Computer-Architecture-6th/) → [04–07 内核/TLPI](../04-Linux-Kernel-Development/) → [08 MikanOS](../08-system-low-level-hands-on/01-mikan-os/) |

**一句话：** CSAPP 建立硬件与程序图景；**本章把 C 写熟**；Hennessy 再量化 CPU/缓存；后面 OS/内核才能顺。

---

## 书目与笔记

📋 裁剪 → [OUTLINE.md](./OUTLINE.md)

| 优先级 | 书目 |
|--------|------|
| 🔴 | K&R · *Pointers on C* |
| 🟡 | 《嵌入式 C 语言自我修养》 |
| 🟡 | [01 CSAPP](../01-CSAPP-3rd/) Ch2–3（与 C 对照） |

---

## 与 09 C++ 的分工

**02 C** = 01 后立刻 · 系统级指针与内存  
**09 C++** = 08 OS / 07 TLPI 后 · muduo/HFT 引擎

→ [09-cpp-learning-notes](../09-cpp-learning-notes/) · [HFT 主次](../08-system-low-level-hands-on/HFT-AND-EMBEDDED-PRIORITY.md)

---

## 下一步

[03-Computer-Architecture-6th](../03-Computer-Architecture-6th/)
