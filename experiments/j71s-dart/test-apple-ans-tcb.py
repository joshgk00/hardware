#!/usr/bin/env python3
"""Test actual descriptor builder with golden values and failure atomicity."""
from pathlib import Path
import subprocess,tempfile
src=(Path(__file__).parent/'driver-patch/include/linux/apple-ans-tcb.h').read_text()
func=src[src.index('static inline int apple_ans_build_tcb'):src.index('\n#endif')]
p=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
typedef uint32_t u32;typedef uint64_t u64;typedef u64 dma_addr_t;
#define U32_MAX UINT32_MAX
#define APPLE_ANS_NVMMU_MAX_REQS 36
#define APPLE_ANS_NVMMU_MAX_PAGES 256
#define APPLE_ANS_NVMMU_PAGE_SIZE 4096
#define APPLE_ANS_TCB_BYTES 0x80
#define APPLE_ANS_FLATDMA_BASE 0x40000000ULL
#define APPLE_ANS_FLATDMA_STRIDE (8ULL * 1024 * 1024)
#define IS_ALIGNED(x,a) (((x)&((a)-1))==0)
#define check_add_overflow(a,b,c) __builtin_add_overflow(a,b,c)
'''
t=r'''
int main(void){u32 tcb[32],sgl[256],saved_tcb[32],saved_sgl[256];u64 pages[256]={0x80001000,0x80003000},addr,iova;
 memset(tcb,0xa5,sizeof(tcb));memset(sgl,0xa5,sizeof(sgl));
 if(apple_ans_build_tcb(tcb,sgl,0x100000,3,pages,2,&iova))abort();
 memcpy(&addr,&tcb[4],8);
 if(tcb[0]!=0x300||tcb[1]!=2||tcb[2]!=0x80001||sgl[0]!=0x80001||sgl[1]!=0x80003||sgl[2]!=0||addr!=0x100c00||iova!=0x41800000)abort();
 memcpy(saved_tcb,tcb,sizeof(tcb));memcpy(saved_sgl,sgl,sizeof(sgl));
 pages[1]=0x80003001;if(apple_ans_build_tcb(tcb,sgl,0x100000,3,pages,2,&iova)!=-EINVAL)abort();
 if(memcmp(tcb,saved_tcb,sizeof(tcb))||memcmp(sgl,saved_sgl,sizeof(sgl)))abort();
 pages[1]=1ULL<<44;if(apple_ans_build_tcb(tcb,sgl,0x100000,3,pages,2,&iova)!=-EINVAL)abort();
 pages[1]=0x80003000;if(apple_ans_build_tcb(tcb,sgl,UINT64_MAX-100,3,pages,2,&iova)!=-EOVERFLOW)abort();
 if(memcmp(tcb,saved_tcb,sizeof(tcb))||memcmp(sgl,saved_sgl,sizeof(sgl)))abort();
 if(apple_ans_build_tcb(tcb,sgl,0,36,pages,2,&iova)!=-EINVAL||apple_ans_build_tcb(tcb,sgl,0,0,NULL,1,&iova)!=-EINVAL||apple_ans_build_tcb(tcb,sgl,0,0,pages,0,&iova)!=-EINVAL||apple_ans_build_tcb(tcb,sgl,0,0,pages,257,&iova)!=-EINVAL)abort();
 for(int i=0;i<256;i++)pages[i]=(u64)i*4096;
 if(apple_ans_build_tcb(tcb,sgl,0x100000,35,pages,256,&iova)||sgl[255]!=255||tcb[1]!=256||iova!=0x51800000)abort();
}
'''
with tempfile.TemporaryDirectory() as d:
 pth=Path(d);(pth/'t.c').write_text(p+func+t)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(pth/'t.c'),'-o',str(pth/'t')],check=True)
 subprocess.run([str(pth/'t')],check=True)
print('ANS TCB golden encoding, limits and failure atomicity passed.')
