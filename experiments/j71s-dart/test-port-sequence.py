#!/usr/bin/env python3
"""Exercise the actual J71s experiment's MMIO guard and restore in a C mock."""
from pathlib import Path
import subprocess, tempfile, sys
if len(sys.argv) != 2:
    raise SystemExit('usage: test-port-sequence.py PATCHED_APPLE_DART_C')
s = Path(sys.argv[1]).read_text()
start = s.index('\t\tif (of_property_read_bool(dev->of_node, "orchard,shared-bits-test")) {')
open_brace = s.index('{', start)
depth = 1
end = open_brace + 1
while depth:
    if s[end] == '{': depth += 1
    elif s[end] == '}': depth -= 1
    end += 1
block = s[start:end]
prefix = r'''
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <stdlib.h>
typedef uint32_t u32;
#define __iomem
#define U32_MAX UINT32_MAX
#define BIT(x) (1U << (x))
#define GENMASK(h,l) (((~0U) >> (31-(h))) & (~0U << (l)))
#define DART_S5L8960X_STREAM_COMMAND_BUSY BIT(3)
#define DART_S5L8960X_STREAM_COMMAND_INVALIDATE BIT(1)
#define DART_S5L8960X_STREAM_COMMAND_SID_SHIFT 8
#define DART_STREAM_COMMAND_BUSY_TIMEOUT 100
#define readl_poll_timeout_atomic(addr,val,cond,delay,timeout) ((val)=readl(addr), (cond) ? 0 : -ETIMEDOUT)
#define readl_poll_timeout(addr,val,cond,delay,timeout) ((val)=readl(addr), (cond) ? 0 : -ETIMEDOUT)
struct device { void *of_node; };
static unsigned char pmgr[0x400], common[0x8000], port[0x4000], dart[0x4000];
static unsigned offsets[16], vals[16], writes, restores_report;
static unsigned long long failed_map;
static unsigned dart_writes; static int emulate_busy;
static void *devm_ioremap(struct device *d, unsigned long long base, size_t n) {
 (void)d; (void)n;
 if (base == failed_map) return NULL;
 switch(base) {case 0x600000000ULL:return common;case 0x601000000ULL:return port;case 0x601008000ULL:return dart;default:abort();}
}
static u32 readl(const void *p) { u32 v; memcpy(&v,p,4); return v; }
static void writel(u32 v, void *p) {
 if ((unsigned char *)p == dart) { if (v != 0xf02) abort(); dart_writes++; u32 after = emulate_busy ? 8 : 0; memcpy(p,&after,4); return; }
 if ((unsigned char *)p < common || (unsigned char *)p >= common+sizeof(common)) abort();
 offsets[writes]=(unsigned)((unsigned char *)p-common); vals[writes++]=v; memcpy(p,&v,4);
}
static int of_property_read_bool(void *n, const char *p) {(void)n;(void)p;return 1;}
static void udelay(unsigned n) { if(n!=100) abort(); }
static void log_info(struct device *d,const char *fmt,...) {(void)d;(void)fmt;restores_report++;}
#define dev_info log_info
#define dev_err log_info
static int run(void) { struct device obj={0}, *dev=&obj; void *test_pmgr=pmgr;
'''
suffix = r'''
 return 99; }
static void put(unsigned char *p,unsigned off,u32 v) {memcpy(p+off,&v,4);}
static void setup(void) {
 memset(pmgr,0,sizeof(pmgr)); memset(common,0,sizeof(common)); memset(port,0xff,sizeof(port)); memset(dart,0xff,sizeof(dart)); writes=restores_report=0; failed_map=0; dart_writes=0; emulate_busy=0;
 put(pmgr,0x310,0xf0);put(pmgr,0x318,0xf0);put(pmgr,0x148,0xf0);put(pmgr,0x320,0xf0);
 put(common,0x124,0x20);put(common,0x114,0x32);put(common,0x100,0x6e);put(common,0x12c,1);put(common,0x2c,0x10);
}
static void expect(int v,const char *why){if(!v){fprintf(stderr,"FAIL %s\n",why);exit(1);}}
int main(void) {
 setup();expect(run()==-ENODEV,"normal return");expect(writes==7,"write count");
 unsigned eoff[]={0x124,0x114,0x100,0x124,0x100,0x114,0x124};
 u32 eval[]={0x20,0x33,0x6f,0x21,0x6e,0x32,0x20};
 for(int i=0;i<7;i++){expect(offsets[i]==eoff[i],"order");if(vals[i]!=eval[i]) fprintf(stderr,"i=%d got=%x want=%x\n",i,vals[i],eval[i]);expect(vals[i]==eval[i],"value");}
 expect(readl(common+0x124)==0x20 && readl(common+0x114)==0x32 && readl(common+0x100)==0x6e,"restore");
 setup(); put(port,0x210,0);put(dart,0,0);expect(run()==-ENODEV,"ready result");expect(dart_writes==1,"one guarded invalidate");expect(writes==7,"restore after invalidate");
 setup(); put(port,0x210,0);put(dart,0,8);expect(run()==-ENODEV,"busy result");expect(dart_writes==0,"busy command skipped");expect(writes==7,"restore after busy");
 setup(); put(port,0x210,0);put(dart,0,0);emulate_busy=1;expect(run()==-ENODEV,"timeout result");expect(dart_writes==1,"one timed-out command");expect(writes==7,"restore after timeout");
 setup(); put(dart,0,0);expect(run()==-ENODEV,"port absent result");expect(dart_writes==0,"unavailable port skipped");
 setup();put(common,0x12c,0);put(port,0x210,0);put(dart,0,0);expect(run()==-ENODEV,"not-ready abort");expect(writes==6 && dart_writes==0,"no DART write before ready");expect(readl(common+0x124)==0x20 && readl(common+0x114)==0x32 && readl(common+0x100)==0x6e,"not-ready restore");
 setup();put(common,0x12c,U32_MAX);put(port,0x210,0);put(dart,0,0);expect(run()==-ENODEV,"all-ones ready abort");expect(writes==6 && dart_writes==0,"no DART write on all-ones ready");
 setup();put(common,0x2c,0);expect(run()==-ENODEV,"global not-ready abort");expect(writes==5 && dart_writes==0,"global timeout restored before port enable");expect(readl(common+0x124)==0x20 && readl(common+0x114)==0x32 && readl(common+0x100)==0x6e,"global timeout restore");
 setup();put(common,0x2c,U32_MAX);expect(run()==-ENODEV,"global all-ones abort");expect(writes==5 && dart_writes==0,"global all-ones restored");
 const unsigned long long mappings[]={0x600000000ULL,0x601000000ULL,0x601008000ULL};
 for(int i=0;i<3;i++){setup();failed_map=mappings[i];expect(run()==-ENOMEM,"failed map rejected");expect(writes==0,"no writes after map failure");}
 const unsigned gate[]={0x310,0x318,0x148,0x320};
 for(int i=0;i<4;i++){setup();put(pmgr,gate[i],0);expect(run()==-EIO,"inactive gate rejected");expect(writes==0,"no gate writes");}
 const unsigned reg[]={0x124,0x114,0x100};
 for(int i=0;i<3;i++){setup();put(common,reg[i],U32_MAX);expect(run()==-EIO,"all ones rejected");expect(writes==0,"no all-ones writes");
 setup();put(common,reg[i],1);expect(run()==-EIO,"bit-one rejected");expect(writes==0,"no wrong-baseline writes");}
 puts("Actual diagnostic block: guarded baselines, write sequence and restoration passed in MMIO mock.");return 0;
}
'''
with tempfile.TemporaryDirectory() as d:
    source=Path(d)/'test.c'; binary=Path(d)/'test'
    source.write_text(prefix+block+suffix)
    subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(source),'-o',str(binary)],check=True)
    subprocess.run([str(binary)],check=True)
