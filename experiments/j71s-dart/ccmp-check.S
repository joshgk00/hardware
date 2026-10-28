.text
.global _start
_start:
 mov w12, #0
 mov w8, #0
 bl check
 orr w12, w12, w0
 mov w8, #8
 bl check
 orr w12, w12, w0, lsl #1
 mov w8, #0x1000
 bl check
 orr w12, w12, w0, lsl #2
 mov w8, #0x1008
 bl check
 orr w12, w12, w0, lsl #3
 mov w0, w12
 mov x8, #93
 svc #0
check:
 and w9, w8, #8
 cmp w8, #1, lsl #12
 ccmp w9, #0, #4, cs
 cset w0, eq
 ret
