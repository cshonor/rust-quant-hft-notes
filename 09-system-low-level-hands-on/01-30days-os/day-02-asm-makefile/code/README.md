# Day 2 · Makefile 参考

| 文件 | 说明 |
|------|------|
| [helloos.asm](./helloos.asm) | 启动区源码（512 B 引导扇区，`ORG 0x7C00` + `55 AA`） |
| [Makefile](./Makefile) | **`make ipl`** → `ipl.bin`；`make clean` 清理 |

**用法：**

```bash
cd day-02-asm-makefile/code
make ipl          # 生成 ipl.bin（512 B）
make clean
```

等价命令：`nasm -f bin helloos.asm -o ipl.bin`

**自检：** `ipl.bin` 大小 **512**；HxD 偏移 **`0x1FE`** 为 **`55 AA`**。

完整说明：[section-2.4](../notes/section-2.4-Makefile-入门.md) · 机器码对照：[Day 1 §1.3](../../day-01-boot-asm/notes/section-1.3-初次体验汇编程序.md)
