# §3.4 · Bootpack — asm + C (four-file division)

Day 3 **bootpack** is built from three sources here, plus **IPL** in [sec-3.1-ipl-int13-disk-load](../sec-3.1-ipl-int13-disk-load/).

| File | Mode | Role |
|------|------|------|
| [../sec-3.1-ipl-int13-disk-load/ipl.asm](../sec-3.1-ipl-int13-disk-load/ipl.asm) | 16-bit | Read bootpack from disk → `JMP 0x8200` |
| [nasmhead.asm](./nasmhead.asm) | 16→32 | VGA `INT 0x10`, A20, GDT, CR0, **`call HariMain`** |
| [bootpack.c](./bootpack.c) | 32-bit C | **`HariMain`** — black screen + main loop |
| [asmfunc.asm](./asmfunc.asm) | 32-bit asm | **`io_hlt`** — `HLT` + `RET` for C |

Notes: [§3.4.2 four-file table](../../notes/section-3.4.2-io_hlt与工程分层.md)

---

## Link bootpack (Linux / WSL / MSYS2)

Load address must match IPL jump target **`0x8200`**.

```bash
cd sec-3.4-bootpack-asm-and-c
nasm -f elf32 nasmhead.asm -o nasmhead.o
nasm -f elf32 asmfunc.asm   -o asmfunc.o
gcc -m32 -c bootpack.c -o bootpack.o -ffreestanding -nostdlib -fno-pie
ld -m elf_i386 -Ttext 0x8200 -e start -o bootpack.bin \
   nasmhead.o bootpack.o asmfunc.o --oformat binary
```

Write **`ipl.bin`** at offset 0 and **`bootpack.bin`** at offset 512 into `haribote.img` (see §3.1 README), then QEMU.

> Simplified teaching tree — haribote-os Makefile adds more objects and exact disk layout from later chapters.

---

## Runtime order

```text
IPL (16-bit) → nasmhead (16→32) → HariMain (C) → io_hlt (asm)
```

Minimal GDT-only variant (no VGA / no io_hlt): [sec-3.4-minimal-16-to-32-call-c](../sec-3.4-minimal-16-to-32-call-c/).
