#!/usr/bin/env python3
"""Compile the validation helper carried by the experimental H9P patch."""
from pathlib import Path
import subprocess
import tempfile
patch = Path(__file__).with_name('h9p-validate-pages.patch').read_text()
added = '\n'.join(line[1:] for line in patch.splitlines() if line.startswith('+') and not line.startswith('+++'))
start = added.index('static bool apple_h9p_nvmmu_valid_pages(')
end = added.index('\n}', start) + 2
helper = added[start:end]
prefix = r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
typedef uint64_t u64;
#define U32_MAX UINT32_MAX
#define APPLE_ANS_NVMMU_PAGE_SIZE 4096
#define IS_ALIGNED(x,a) (((x)&((a)-1))==0)
#define ilog2(x) 12
'''
suffix = r'''
int main(void) {
 u64 valid[] = {0, 0x80001000ULL, (u64)UINT32_MAX << 12};
 u64 unaligned[] = {0x80001001ULL};
 u64 overflow[] = {((u64)UINT32_MAX + 1) << 12};
 u64 mixed[] = {0x1000, 0x2001};
 if (!apple_h9p_nvmmu_valid_pages(NULL, 0) ||
     apple_h9p_nvmmu_valid_pages(NULL, 1) ||
     !apple_h9p_nvmmu_valid_pages(valid, 3) ||
     apple_h9p_nvmmu_valid_pages(unaligned, 1) ||
     apple_h9p_nvmmu_valid_pages(overflow, 1) ||
     apple_h9p_nvmmu_valid_pages(mixed, 2)) abort();
}
'''
with tempfile.TemporaryDirectory() as d:
    p = Path(d)
    (p / 'test.c').write_text(prefix + helper + suffix)
    subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', str(p / 'test.c'), '-o', str(p / 'test')], check=True)
    subprocess.run([str(p / 'test')], check=True)
print('H9P page alignment and representable-address checks passed.')
