# Day 1 · helloos 映像参考文件

> 与 [day-01-boot-asm](../../08-1-30days-os/day-01-boot-asm/) 笔记配套 · 非 tolset 版权资源，仅为学习对照用字节表

| 文件 | 说明 |
|------|------|
| [helloos.img](./helloos.img) | 完整 **1,474,560 B** 软盘映像，可直接 `qemu-system-i386 -fda helloos.img` |
| [helloos-boot-sector.bin](./helloos-boot-sector.bin) | 仅引导扇区 **512 B** |
| [helloos-boot-sector.hex](./helloos-boot-sector.hex) | 512 字节 · 16 字节/行，HxD 对照用 |
| [helloos-boot-sector-paste.txt](./helloos-boot-sector-paste.txt) | 512 字节 · 单行空格分隔，便于复制 |

完整进制说明见 [HELLOOS_HEX_REFERENCE.md](../../08-1-30days-os/HELLOOS_HEX_REFERENCE.md)。

**HxD 用法（引导扇区）：**

1. 新建/打开 `boot.img` → `Ctrl+E` → `1474560`
2. 偏移 `0` 起：打开 `helloos-boot-sector.hex` 对照输入，或从 tolset 工程复制
3. `Ctrl+G` → `1FE` → 确认 `55 AA`
4. 也可直接复制本目录 **`helloos.img`** 到桌面运行
