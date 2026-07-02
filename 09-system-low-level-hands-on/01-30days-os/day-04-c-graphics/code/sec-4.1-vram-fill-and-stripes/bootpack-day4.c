/* Day 4 §4.1 · VRAM white fill + stripes (haribote / QEMU)
 * Replace HariMain in Day 3 bootpack.c, or use this file as bootpack.c when linking.
 * Mode 0x13 must already be set by nasmhead.asm (INT 0x10, AX=0x0013).
 */

void io_hlt(void);

#define VRAM_BASE   0xA0000
#define SCREEN_W    320
#define SCREEN_H    200
#define TOTAL_PIX   (SCREEN_W * SCREEN_H)
#define PIXEL_BLACK 0
#define PIXEL_WHITE 15   /* book default palette; index 1 is often blue, not white */

static void fill_screen(volatile unsigned char *vram, unsigned char color)
{
    int i;

    for (i = 0; i < TOTAL_PIX; i++) {
        vram[i] = color;
    }
}

/* Stage 2a: 8-pixel-wide vertical bars via AND mask on x */
static void draw_stripes_x_mask(volatile unsigned char *vram)
{
    int x, y;

    for (y = 0; y < SCREEN_H; y++) {
        for (x = 0; x < SCREEN_W; x++) {
            vram[y * SCREEN_W + x] = (x & 8) ? PIXEL_BLACK : PIXEL_WHITE;
        }
    }
}

/* Stage 2b: XOR-style odd/even columns via i & 1 */
static void draw_stripes_xor_cols(volatile unsigned char *vram)
{
    int i;

    for (i = 0; i < TOTAL_PIX; i++) {
        vram[i] = (i & 1) ? PIXEL_WHITE : PIXEL_BLACK;
    }
}

void HariMain(void)
{
    volatile unsigned char *vram = (volatile unsigned char *)VRAM_BASE;

    /* --- pick ONE demo (comment/uncomment) --- */

    fill_screen(vram, PIXEL_WHITE);           /* QEMU: full white */
    /* draw_stripes_x_mask(vram); */          /* 8px vertical bars */
    /* draw_stripes_xor_cols(vram); */        /* 1px vertical bars */

    for (;;) {
        io_hlt();
    }
}
