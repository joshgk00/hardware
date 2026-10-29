#!/usr/bin/env python3
"""Test the real descriptor wrapper and builder with mocked DMA allocation."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).parent/'driver-patch'
builder=(root/'include/linux/apple-ans-tcb.h').read_text()
builder=builder[builder.index('static inline int apple_ans_build_tcb'):builder.index('\n#endif')]
wrapper=(root/'j71s-identify-descriptor.h').read_text()
wrapper=wrapper[wrapper.index('struct j71s_identify_descriptor'):]
preamble=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
typedef uint32_t u32;typedef uint64_t u64;typedef uint64_t dma_addr_t;
#define __maybe_unused
#define PAGE_SIZE 16384
#define SZ_4K 4096
#define GFP_KERNEL 0
#define __GFP_ZERO 0
#define U32_MAX UINT32_MAX
#define DMA_BIT_MASK(n) ((1ULL<<(n))-1)
#define IS_ALIGNED(a,n) (((a)&((n)-1))==0)
#define check_add_overflow(a,b,c) __builtin_add_overflow(a,b,c)
#define WRITE_ONCE(x,v) ((x)=(v))
#define dma_wmb() ((void)0)
#define APPLE_ANS_NVMMU_MAX_REQS 36
#define APPLE_ANS_NVMMU_MAX_PAGES 256
#define APPLE_ANS_NVMMU_PAGE_SIZE 4096
#define APPLE_ANS_TCB_BYTES 0x80
#define APPLE_ANS_TCB_READ 0x100
#define APPLE_ANS_TCB_WRITE 0x200
#define APPLE_ANS_FLATDMA_BASE 0x40000000ULL
#define APPLE_ANS_FLATDMA_STRIDE (8ULL*1024*1024)
#define J71S_IDENTIFY_FLATDMA 0x40000000ULL
struct device {int unused;};
struct j71s_identify_preparation {void *payload;u64 payload_phys;bool armed,descriptor_published;};
struct scatterlist {u64 physical;unsigned int length;};
struct sg_table {int nents;struct scatterlist *sgl;};
static struct scatterlist sg;static u64 next_dma=0x200000;static int alloc_fail,sg_error,wrong_phys,free_count;static bool locked=true;
static bool j71s_test_kexec_locked(void){return locked;}
static void *dma_alloc_coherent(struct device *h,size_t n,dma_addr_t *d,int flags){(void)h;(void)flags;if(alloc_fail)return NULL;*d=next_dma;return calloc(1,n);}
static void dma_free_coherent(struct device *h,size_t n,void *p,dma_addr_t d){(void)h;(void)n;(void)d;free_count++;free(p);}
static int dma_get_sgtable(struct device *h,struct sg_table *t,void *p,dma_addr_t d,size_t n){(void)h;(void)p;if(sg_error)return -EIO;sg.physical=d+(wrong_phys?4096:0);sg.length=n;t->nents=1;t->sgl=&sg;return 0;}
static u64 sg_phys(struct scatterlist *s){return s->physical;}
static void sg_free_table(struct sg_table *s){(void)s;}
'''
checks=r'''
int main(void){struct device host={0};int payload;struct j71s_identify_preparation p={.payload=&payload,.payload_phys=0x100000};struct j71s_identify_descriptor d={0};u32 tcb[32]={0};
 locked=false;if(j71s_identify_prepare_descriptor(&host,&p,tcb,&d)!=-EINVAL||d.sgl||free_count)abort();locked=true;
 alloc_fail=1;if(j71s_identify_prepare_descriptor(&host,&p,tcb,&d)!=-ENOMEM||d.sgl||free_count)abort();alloc_fail=0;
 next_dma=0x200001;if(j71s_identify_prepare_descriptor(&host,&p,tcb,&d)!=-ERANGE||d.sgl||free_count!=1)abort();
 next_dma=1ULL<<36;if(j71s_identify_prepare_descriptor(&host,&p,tcb,&d)!=-ERANGE||d.sgl||free_count!=2)abort();
 next_dma=0x200000;sg_error=1;if(j71s_identify_prepare_descriptor(&host,&p,tcb,&d)!=-EIO||d.sgl||free_count!=3)abort();sg_error=0;
 wrong_phys=1;if(j71s_identify_prepare_descriptor(&host,&p,tcb,&d)!=-ERANGE||d.sgl||free_count!=4)abort();wrong_phys=0;
 p.payload_phys=0x100001;if(j71s_identify_prepare_descriptor(&host,&p,tcb,&d)!=-EINVAL||d.sgl||free_count!=5||tcb[1])abort();
 p.payload_phys=0x100000;if(j71s_identify_prepare_descriptor(&host,&p,tcb,&d)||!d.published||!p.descriptor_published||tcb[0]!=0x200||tcb[1]!=1||tcb[2]!=0x100||d.sgl[0]!=0x100||free_count!=5)abort();
 if(j71s_identify_prepare_descriptor(&host,&p,tcb,&d)!=-EINVAL||free_count!=5)abort();
 free(d.sgl); /* Test process only; real hardware must retain this allocation. */
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'test.c').write_text(preamble+builder+wrapper+checks)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('Identify descriptor allocation, identity, publication and retention passed.')
