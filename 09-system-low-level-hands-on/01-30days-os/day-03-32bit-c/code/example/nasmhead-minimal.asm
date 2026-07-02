; 教学示例 · 16 位切 32 位 + call C（非完整 haribote，仅供 §3.4 对照）
; 对应原书 nasmhead.asm 的极简版；C 入口在原书里叫 HariMain

        BITS 16

; 假设 CPU 已在 16 位实模式运行到此（IPL 已读盘、BIOS 事已做完）
        GLOBAL switch_to_32

switch_to_32:
        cli
        lgdt [gdt_desc]

        mov     eax, cr0
        or      eax, 1
        mov     cr0, eax

        ; 远跳转：刷新流水线，进入 32 位代码段
        jmp     CODE_SEL:init_pm

        BITS 32
init_pm:
        mov     ax, DATA_SEL
        mov     ds, ax
        mov     es, ax
        mov     fs, ax
        mov     gs, ax
        mov     ss, ax
        mov     esp, 0x90000

        ; 「舞台搭好」→ 调用 C 写的 kernel_main（原书 HariMain）
        extern  kernel_main
        call    kernel_main

        ; C 若返回，停住
hang:
        hlt
        jmp     hang

        BITS 16
; --- GDT（平坦 4GB 代码/数据段，教学用）---
align 8
gdt:
        dq      0
        dq      0x00cf9a000000ffff      ; 代码段
        dq      0x00cf92000000ffff      ; 数据段
gdt_end:

gdt_desc:
        dw      gdt_end - gdt - 1
        dd      gdt

CODE_SEL  equ 0x08
DATA_SEL  equ 0x10
