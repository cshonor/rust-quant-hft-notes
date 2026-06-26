# Day 2 · 启动区 IPL + Makefile
# 说明：notes/section-2.4-Makefile-入门.md
# 用法：make ipl  →  helloos.asm 编译为 ipl.bin（512 B）

NASM = nasm
NASMFLAGS = -f bin

.PHONY: all clean ipl

all: ipl

ipl: helloos.asm
	$(NASM) $(NASMFLAGS) $< -o $@

clean:
	rm -f ipl.bin os-image.bin
