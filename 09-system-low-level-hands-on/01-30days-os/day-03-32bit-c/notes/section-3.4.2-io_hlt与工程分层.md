## ④.2 `io_hlt` 与工程分层

### 四文件分工

| 文件 | 后缀 | 职责 |
|------|------|------|
| **`ipl.asm`** | `.asm` | **512 B 引导** — 全汇编，尚无 C |
| **`nasmhead.asm`** | `.asm` | **切 VGA、A20、GDT、进 32 位** — C 跑之前 |
| **`bootpack.c`** | `.c` | **`HariMain`**、OS 主逻辑 |
| **`asmfunc.asm`** | `.asm` | **`io_hlt`** 等 C 调用的 **底层原语** |

```text
ipl.asm（16 位，512B）     读盘 — 尚无 C
    ↓
nasmhead.asm（16→32）      模式切换 — 仍必须汇编
    ↓
bootpack.c（32 位 C）      HariMain 主逻辑
    +
asmfunc.asm（32 位 asm）   io_hlt 等「补丁」
```

**你现在：** [ipl.asm](../code/ipl.asm) **全是汇编** — 等 bootpack 链起来，会 **`.asm` + `.c` 一起链接**。

---

### 典型例子：`io_hlt`

**asmfunc.asm（示意）：**

```nasm
        BITS 32
        GLOBAL io_hlt

io_hlt:
        HLT
        RET
```

**bootpack.c（示意）：**

```c
void io_hlt(void);

void HariMain(void) {
    for (;;) {
        io_hlt();
    }
}
```

| 谁 | 干什么 |
|----|--------|
| **C** | 决定 **什么时候** 休眠 |
| **汇编** | 执行 **HLT** |
| **链接器** | 把 `call io_hlt` 连到 asm 入口 |

更大块：**nasmhead** 里 **GDT + CR0** 整段留在 asm，切完后 **`call HariMain`** — 见 [§3.4.3](./section-3.4.3-16切32与call-C完整例子.md)。

---

← [§3.4.1 为何需要 asm](./section-3.4.1-为何C需要汇编包装.md) · [§3.4.3 完整例子 →](./section-3.4.3-16切32与call-C完整例子.md)
