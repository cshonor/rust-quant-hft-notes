## 7.1–7.3 编译驱动与目标文件

### 7.1 编译器驱动程序

`gcc` 等是 **驱动 (driver)**，背后调用 cpp、cc1、as、ld：

```bash
gcc -Og -Wall -o prog main.c sum.c
# 等价于：编译各 .c → .o → ld 链接
```

常用分解：

```bash
gcc -c main.c -o main.o    # 只到目标文件
gcc main.o sum.o -o prog   # 只链接
```

**HFT：** CI 显式 `-c` 再 link，便于 **缓存 object**、LTO 统一链接阶段。

### 7.2 静态链接

- 链接器 **把所有需要的 `.o` 和库代码拷贝** 进可执行文件
- **优点：** 无运行时找 `.so`、部署简单、启动可预测
- **缺点：** 体积大、libc/security 更新需重链

**HFT 常见：** 关键二进制 **部分或全静态**（`-static` 慎用 glibc；更常静态第三方、动态 libc 或 musl）；或 **pinned** 的 `.so` 版本随镜像分发。

### 7.3 目标文件

**ELF (Executable and Linkable Format)** — Linux 标准

| 类型 | 典型扩展 | 说明 |
|------|----------|------|
| **可重定位 (REL)** | `.o` | 待链接 |
| **可执行 (EXEC)** | `a.out` | 可直接跑 |
| **共享 (DYN)** | `.so` | 动态库 |

```bash
file main.o prog
readelf -h main.o
```

---

← [本章导读](../README.md)
