# 08-1 · 30 天自制操作系统

> **父模块：** [08-system-low-level-hands-on](../README.md)  
> **参考：** 川合秀实《30 天自制操作系统》· 本仓库为 HFT 学习链裁剪笔记 + 实验记录

## 定位

从 **零启动** 写出一个能跑多任务、有中断和内存管理的最小 OS — 把 LKD / CSAPP 里「进程、中断、页表」从 **读者** 变成 **作者**。

## 建议阶段（待按原书章节补 OUTLINE）

| 阶段 | 主题 | HFT 关联 |
|------|------|----------|
| Day 1–7 | 引导、实模式→保护模式、显存/键盘 | 理解启动与裸机环境 |
| Day 8–15 | GDT/IDT、中断、时钟 | **上下文切换** 从哪来 |
| Day 16–23 | 内存分配、页表、多任务 | TLB / 缺页 / 绑内存直觉 |
| Day 24–30 | 文件、API、Shell | 与 Linux syscall 对照 |

## 产出

- [ ] `OUTLINE.md` — 按原书 Day 裁剪 🔴/🟡/⚪
- [ ] `code/` — 可启动镜像与实验 diff
- [ ] 与 [05-LKD](../05-Linux-Kernel-Development/) Ch4/7/8 对照表

## 交叉阅读

- [01-CSAPP Ch8/9](../../01-CSAPP-3rd/chapter-08-exceptional-control-flow/) · [05-LKD](../../05-Linux-Kernel-Development/)
- 下一步：[08-2-30days-cpu](../08-2-30days-cpu/)
