#!/usr/bin/env python3
"""Test the actual S8000 property reader with synthetic device-tree data."""
from pathlib import Path
import subprocess
import tempfile
h = (Path(__file__).parent / 'driver-patch/include/linux/apple-s8000-tunables.h').read_text()
body = h[h.index('struct apple_s8000_tunable'):h.rindex('#endif')]
prefix = r'''
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
typedef uint32_t u32;
struct device_node { u32 *cells; int count; int fail_index; };
static int of_property_count_u32_elems(struct device_node *n,const char *p) {(void)p;return n->count;}
static int of_property_read_u32_index(struct device_node *n,const char *p,unsigned int i,u32 *v) {(void)p;if ((int)i==n->fail_index || (int)i>=n->count) return -EINVAL;*v=n->cells[i];return 0;}
'''
suffix = r'''
static void check(int v) { if (!v) abort(); }
int main(void) {
 u32 c[]={4,0xff,0x20,12,0xffff,0x1234};
 struct device_node n={c,6,-1}; struct apple_s8000_tunable out[2];
 check(!apple_s8000_read_tunables(&n,"x",out,2,16));
 check(out[0].offset==4 && out[0].mask==0xff && out[0].value==0x20 && out[1].offset==12);
 n.count=5;check(apple_s8000_read_tunables(&n,"x",out,2,16)==-EINVAL);n.count=6;
 c[0]=2;check(apple_s8000_read_tunables(&n,"x",out,2,16)==-EINVAL);c[0]=4;
 c[3]=16;check(apple_s8000_read_tunables(&n,"x",out,2,16)==-EINVAL);c[3]=12;
 c[2]=0x100;check(apple_s8000_read_tunables(&n,"x",out,2,16)==-EINVAL);c[2]=0x20;
 n.fail_index=5;check(apple_s8000_read_tunables(&n,"x",out,2,16)==-EINVAL);n.fail_index=-1;
 check(apple_s8000_read_tunables(&n,"x",out,0,16)==-EINVAL);
 check(apple_s8000_read_tunables(&n,"x",out,257,16)==-EINVAL);
 check(apple_s8000_read_tunables(&n,"x",out,2,3)==-EINVAL);
 puts("S8000 tunable reader validates complete tables before MMIO.");
}
'''
with tempfile.TemporaryDirectory() as d:
    p = Path(d); (p/'t.c').write_text(prefix + body + suffix)
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',str(p/'t.c'),'-o',str(p/'t')],check=True)
    subprocess.run([str(p/'t')],check=True)
