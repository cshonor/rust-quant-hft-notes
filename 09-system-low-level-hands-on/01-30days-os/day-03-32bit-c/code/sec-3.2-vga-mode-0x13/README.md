# §3.2 · VGA mode 0x13 (haribote black screen)

§3.2 has **no separate source file** — the VGA switch lives in **nasmhead.asm** before entering 32-bit mode:

```nasm
        mov     ax, 0x0013        ; 320×200×256, palette mode
        int     0x10              ; BIOS video services (16-bit only)
```

See the full entry in [sec-3.4-bootpack-asm-and-c/nasmhead.asm](../sec-3.4-bootpack-asm-and-c/nasmhead.asm).

**Success criterion (book):** after `HariMain` fills `0xA0000` with palette index 0, QEMU shows a **black screen**.

Notes: [§3.2 haribote OS](../../notes/section-3.2-纸娃娃操作系统.md)
