#!/usr/bin/env python3
"""Test the experimental one-cell DART DMA-window validator."""
from pathlib import Path
import subprocess,tempfile
s=(Path(__file__).parent/'driver-patch/include/linux/apple-dart-dma-window.h').read_text()
f=s[s.index('static inline int apple_dart_validate_window'):s.index('\n#endif')]
p=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <errno.h>
typedef uint64_t u64;typedef uint32_t u32;
#define IS_ALIGNED(x,a) (((x)&((a)-1))==0)
#define check_add_overflow(a,b,c) __builtin_add_overflow(a,b,c)
static bool is_power_of_2(u64 x){return x && !(x & (x-1));}
'''
t=r'''
int main(void) {u64 end=0;
 if(apple_dart_validate_window(0x80000000,0x3c000000,4096,32,&end)||end!=0xbbffffff)abort();
 if(apple_dart_validate_window(0,0x100000000ULL,4096,32,&end)||end!=0xffffffff)abort();
 end=123;if(apple_dart_validate_window(0x80000000,0,4096,32,&end)!=-EINVAL||end!=123)abort();
 if(apple_dart_validate_window(0x80000001,0x1000,4096,32,&end)!=-EINVAL)abort();
 if(apple_dart_validate_window(0x80000000,0x1001,4096,32,&end)!=-EINVAL)abort();
 if(apple_dart_validate_window(0x90000000,0x1000,4096,32,&end)!=-EINVAL)abort();
 if(apple_dart_validate_window(0x80000000,0x80001000,4096,32,&end)!=-EINVAL)abort();
 if(apple_dart_validate_window(0xfffffffffffff000ULL,0x2000,4096,63,&end)!=-EINVAL)abort();
 if(apple_dart_validate_window(0,4096,3000,32,&end)!=-EINVAL)abort();
 if(apple_dart_validate_window(0,4096,4096,64,&end)!=-EINVAL)abort();
 if(apple_dart_validate_window(0,4096,4096,32,NULL)!=-EINVAL)abort();
}
'''
with tempfile.TemporaryDirectory() as d:
 pth=Path(d);(pth/'t.c').write_text(p+f+t)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(pth/'t.c'),'-o',str(pth/'t')],check=True)
 subprocess.run([str(pth/'t')],check=True)
print('DART DMA-window bounds, alignment, overflow and mask constraints passed.')
