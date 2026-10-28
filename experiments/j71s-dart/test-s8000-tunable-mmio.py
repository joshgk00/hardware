#!/usr/bin/env python3
"""Exercise the real masked-write and reverse-restoration helper with MMIO mocks."""
from pathlib import Path
import subprocess
import tempfile
h=(Path(__file__).parent/'driver-patch/include/linux/apple-s8000-tunable-mmio.h').read_text()
body=h[h.index('static inline int apple_s8000_apply_tunables'):h.rindex('#endif')]
prefix=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
typedef uint32_t u32;
#define __iomem
#define U32_MAX UINT32_MAX
struct apple_s8000_tunable { u32 offset,mask,value; };
static u32 mem[4]; static int reads,writes,fail_read=-1,fail_write=-1,wrong_read=-1,order[16];
static u32 readl(void *p) {int k=reads++; if (k==fail_read) return U32_MAX;u32 v=*(u32*)p;return k==wrong_read ? v^1 : v;}
static void writel(u32 v,void *p) {int k=writes++;order[k]=(int)((u32*)p-mem);if(k!=fail_write)*(u32*)p=v;}
'''
suffix=r'''
static void check(int x){if(!x)abort();}
static void reset(void){mem[0]=0x1122;mem[1]=0x3344;reads=writes=0;fail_read=fail_write=wrong_read=-1;}
int main(void){
 struct apple_s8000_tunable t[]={{0,0xff,0xaa},{4,0xff,0xbb}};u32 saved[2];unsigned n=0;int ret;
 reset();ret=apple_s8000_apply_tunables(mem,t,2,saved,&n);check(!ret && n==2 && mem[0]==0x11aa && mem[1]==0x33bb);
 check(!apple_s8000_restore_tunables(mem,t,saved,&n) && !n && mem[0]==0x1122 && mem[1]==0x3344 && order[2]==1 && order[3]==0);
 reset();fail_read=2;ret=apple_s8000_apply_tunables(mem,t,2,saved,&n);check(ret==-EIO && n==1);check(!apple_s8000_restore_tunables(mem,t,saved,&n) && mem[0]==0x1122);
 reset();wrong_read=3;ret=apple_s8000_apply_tunables(mem,t,2,saved,&n);check(ret==-EIO && n==2);check(!apple_s8000_restore_tunables(mem,t,saved,&n) && mem[0]==0x1122 && mem[1]==0x3344);
 reset();t[1].offset=0;check(!apple_s8000_apply_tunables(mem,t,2,saved,&n));check(!apple_s8000_restore_tunables(mem,t,saved,&n) && mem[0]==0x1122);t[1].offset=4;
 reset();n=1;check(apple_s8000_apply_tunables(mem,t,2,saved,&n)==-EINVAL && writes==0);n=0;
 reset();check(!apple_s8000_apply_tunables(mem,t,2,saved,&n));fail_write=writes;check(apple_s8000_restore_tunables(mem,t,saved,&n)==1 && n==0);
 puts("S8000 tunable MMIO success, failure and reverse restoration passed.");
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'t.c').write_text(prefix+body+suffix)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(p/'t.c'),'-o',str(p/'t')],check=True)
 subprocess.run([str(p/'t')],check=True)
