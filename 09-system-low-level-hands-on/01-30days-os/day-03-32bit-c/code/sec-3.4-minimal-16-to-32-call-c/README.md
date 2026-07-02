# §3.4.3 · Minimal asm → C (GDT + CR0 only)

**Not a bootable floppy** — shows **nasmhead switches to 32-bit, then `call`s C**.

| File | Role |
|------|------|
| [nasmhead-minimal.asm](./nasmhead-minimal.asm) | CLI, LGDT, CR0.PE, segments, stack, **`call kernel_main`** |
| [kernel_main.c](./kernel_main.c) | Write `"Hello 32-bit C!"` to VGA text buffer `0xB8000` |

Full four-file bootpack (VGA, **`HariMain`**, **`io_hlt`**): [sec-3.4-bootpack-asm-and-c](../sec-3.4-bootpack-asm-and-c/).

Notes: [§3.4.3](../../notes/section-3.4.3-16切32与call-C完整例子.md)

---

## Link (Linux / WSL / MSYS2)

```bash
cd sec-3.4-minimal-16-to-32-call-c
nasm -f elf32 nasmhead-minimal.asm -o nasmhead.o
gcc -m32 -c kernel_main.c -o kernel_main.o -ffreestanding -nostdlib -fno-pie
ld -m elf_i386 -o bootpack.elf nasmhead.o kernel_main.o
```

| This example | Book |
|--------------|------|
| `nasmhead-minimal.asm` | `nasmhead.asm` (+ VGA, A20, …) |
| `kernel_main()` | **`HariMain()`** |
| (omitted) | `asmfunc.asm` → **`io_hlt()`** |
| (omitted) | [ipl.asm](../sec-3.1-ipl-int13-disk-load/ipl.asm) |
