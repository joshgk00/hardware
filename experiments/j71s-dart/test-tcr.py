#!/usr/bin/env python3
"""Execute the patched kernel function against a mocked TCR register."""
from pathlib import Path
import subprocess
import sys
import tempfile


def function(source: str) -> str:
    name = 'static void apple_dart_s5l8960x_write_tcr('
    start = source.index(name)
    body = source.index('{', start)
    depth = 0
    for pos in range(body, len(source)):
        if source[pos] == '{':
            depth += 1
        elif source[pos] == '}':
            depth -= 1
            if depth == 0:
                return source[start:pos + 1]
    raise ValueError('unterminated function')


def main():
    if len(sys.argv) != 2:
        raise SystemExit('Usage: test-tcr.py PATCHED_KERNEL_CHECKOUT')
    src = (Path(sys.argv[1]) / 'drivers/iommu/apple-dart.c').read_text()
    program = r'''
#include <stdint.h>
#include <stdio.h>
typedef uint32_t u32;
#define DART_S5L8960X_TCR_BITS_PER_STREAM 8
#define WARN_ON(x) (x)
struct hw { u32 tcr; };
struct apple_dart { unsigned char *regs; struct hw *hw; int lock; };
static int writes, violations, locked;
#define spin_lock_irqsave(lock, flags) do { (void)(lock); (flags) = 0; if (locked) violations++; locked = 1; } while (0)
#define spin_unlock_irqrestore(lock, flags) do { (void)(lock); (void)(flags); if (!locked) violations++; locked = 0; } while (0)
static u32 readl(void *p) { if (!locked) violations++; return *(u32 *)p; }
static void writel(u32 v, void *p) { if (!locked) violations++; *(u32 *)p = v; writes++; }
''' + function(src) + r'''
int main(void) {
    const u32 expected_enable[] = {0x44332280, 0x44338011, 0x44802211, 0x80332211};
    const u32 expected_disable[] = {0x44332200, 0x44330011, 0x44002211, 0x00332211};
    struct hw hw = { 0 }; u32 reg; struct apple_dart dart = {(unsigned char *)&reg, &hw, 0};
    for (u32 sid = 0; sid < 4; sid++) {
        reg = 0x44332211; writes = 0;
        apple_dart_s5l8960x_write_tcr(&dart, sid, 0x80);
        if (reg != expected_enable[sid] || writes != 1) return 1;
        reg = 0x44332211; writes = 0;
        apple_dart_s5l8960x_write_tcr(&dart, sid, 0);
        if (reg != expected_disable[sid] || writes != 1) return 2;
    }
    reg = 0x44332211; writes = 0;
    apple_dart_s5l8960x_write_tcr(&dart, 4, 0x80);
    apple_dart_s5l8960x_write_tcr(&dart, 1, 0x100);
    if (reg != 0x44332211 || writes || violations || locked) return 3;
    puts("TCR stream updates preserve other streams; invalid arguments do not write");
    return 0;
}
'''
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        (root / 'test.c').write_text(program)
        subprocess.run(['cc', '-std=c11', '-Wall', '-Werror', str(root / 'test.c'), '-o', str(root / 'test')], check=True)
        subprocess.run([str(root / 'test')], check=True)


if __name__ == '__main__':
    main()
