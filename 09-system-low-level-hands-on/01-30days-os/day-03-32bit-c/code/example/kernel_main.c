/* 教学示例 · C 内核入口（§3.4）
 * 原书 bootpack.c 里叫 HariMain，这里用 kernel_main 便于对照通用教程 */

void kernel_main(void) {
    volatile char *vidmem = (volatile char *)0xB8000;
    const char *str = "Hello 32-bit C!";
    int i;

    for (i = 0; str[i] != '\0'; i++) {
        vidmem[i * 2]     = str[i];   /* 字符 */
        vidmem[i * 2 + 1] = 0x07;     /* 属性：灰底黑字（VGA 文本） */
    }

    for (;;) {
        /* 死循环；原书可能 call io_hlt() */
    }
}
