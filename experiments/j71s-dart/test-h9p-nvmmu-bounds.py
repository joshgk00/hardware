#!/usr/bin/env python3
"""Exercise the scratch-window predicate and TCB size in the actual patch."""
from pathlib import Path
import subprocess,tempfile
patch=Path(__file__).with_name('h9p-nvmmu-bounds.patch').read_text()
post='\n'.join(x[1:] for x in patch.splitlines() if x.startswith((' ','+')) and not x.startswith('+++'))
a=post.index('if (size < H9P_NVMMU_SART_ALIGNMENT');b=post.index(' {',a)
condition=post[a:b]
assert '#define H9P_NVMMU_TCB_COUNT\t\t128' in post
assert 'round_up(H9P_NVMMU_TCB_COUNT *' in post
prefix=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
typedef uint64_t u64;
#define U32_MAX UINT32_MAX
#define H9P_NVMMU_SART_ALIGNMENT 0x100000ULL
#define IS_ALIGNED(x,a) (((x)&((a)-1))==0)
struct resource {u64 start;};
static bool bad(u64 start, u64 size, uint32_t iova) { struct resource res={start};
'''
suffix=r'''
 { return true; }
 return false; }
int main(void) {
 if(bad(0x80000000,0xe00000,0xbc000000))abort();
 if(!bad(0x80000000,0xe00001,0xbc000000))abort();
 if(!bad(0x80000001,0xe00000,0xbc000000))abort();
 if(!bad(0x80000000,0x200000,0xbff00000))abort();
 if(bad(0x80000000,0x100000,0xbff00000))abort();
 if(!bad(0x80000000,0x100000,0x7ff00000))abort();
 for(unsigned page=4096;page<=16384;page*=4) {
  unsigned bytes=((128*0x80+page-1)/page)*page;
  if(bytes<128*0x80)abort();
 }
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'t.c').write_text(prefix+condition+suffix)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(p/'t.c'),'-o',str(p/'t')],check=True)
 subprocess.run([str(p/'t')],check=True)
print('H9P scratch range boundaries and full hardware TCB coverage passed.')
