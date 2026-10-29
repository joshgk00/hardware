#!/usr/bin/env python3
"""Test actual scratch setup with fake reserved memory and MMIO."""
from pathlib import Path
import subprocess, tempfile
src=(Path(__file__).parent/'driver-patch/j71s-identify-scratch.h').read_text()
fn=src[src.index('struct j71s_identify_scratch'):]
preamble=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
typedef uint32_t u32;typedef uint16_t u16;
#define __iomem
#define __maybe_unused
#define J71S_SCRATCH_IOVA 0xbc000000U
#define J71S_SCRATCH_BYTES 0xe00000U
#define PCI_COMMAND 4
#define PCI_COMMAND_MASTER 4
#define NVME_REG_CC 0x14
#define NVME_REG_CSTS 0x1c
#define U32_MAX UINT32_MAX
#define SZ_1M 0x100000ULL
#define BIT(n) (1U<<(n))
#define DMA_BIT_MASK(n) ((1ULL<<(n))-1)
#define IS_ALIGNED(a,n) (((a)&((n)-1))==0)
#define IORESOURCE_SYSTEM_RAM 1
#define IORES_DESC_NONE 0
#define REGION_DISJOINT 0
#define MEMREMAP_WB 1
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define wmb() ((void)0)
struct pci_dev {u16 command;};
struct device_node {int unused;};
struct reserved_mem {uint64_t base,size;};
static struct device_node node; static struct reserved_mem region={0x100000000ULL,J71S_SCRATCH_BYTES};
static unsigned char bar_bytes[0x2000],mmu_bytes[0x1000];
static int nwrite,fail_write,unmaps,nodeputs,cache_cleans; static bool locked=true,allow_region=true,valid_node=true;
static bool j71s_test_kexec_locked(void){return locked;}
static int pci_read_config_word(struct pci_dev *d,int where,u16 *v){(void)where;*v=d->command;return 0;}
static struct device_node *of_find_node_by_path(const char *p){(void)p;return valid_node?&node:NULL;}
static struct reserved_mem *of_reserved_mem_lookup(struct device_node *p){(void)p;return &region;}
static bool of_property_read_bool(struct device_node *n,const char *p){(void)n;return !strcmp(p,"no-map");}
static int region_intersects(uint64_t p,uint64_t n,int a,int b){(void)p;(void)n;(void)a;(void)b;return allow_region?0:1;}
static void dcache_clean_poc(unsigned long start,unsigned long end){unsigned char *p=(void*)start;if(end-start!=J71S_SCRATCH_BYTES || nwrite)abort();for(unsigned long i=0;i<end-start;i++)if(p[i])abort();cache_cleans++;}
static void *memremap(uint64_t p,size_t n,int x){(void)p;(void)x;return malloc(n);}
static void memunmap(void *p){unmaps++;free(p);}
static void *ioremap(uint64_t p,size_t n){(void)p;(void)n;return mmu_bytes;}
static void iounmap(void *p){(void)p;unmaps++;}
static void of_node_put(struct device_node *p){(void)p;nodeputs++;}
static u32 readl(const void *p){u32 v;memcpy(&v,p,4);return v;}
static void writel(u32 v,void *p){uintptr_t q=(uintptr_t)p,lo=(uintptr_t)mmu_bytes;size_t off=q-lo;nwrite++;if(nwrite==fail_write)v^=1;if(q>=lo&&q<lo+sizeof(mmu_bytes)&&(off==0x24||off==0x28))v|=BIT(31);memcpy(p,&v,4);}
'''
checks=r'''
static void reset(void){u32 fixed=BIT(31);memset(bar_bytes,0,sizeof(bar_bytes));memset(mmu_bytes,0,sizeof(mmu_bytes));memcpy(mmu_bytes+0x24,&fixed,4);memcpy(mmu_bytes+0x28,&fixed,4);nwrite=0;fail_write=0;unmaps=0;nodeputs=0;cache_cleans=0;locked=true;allow_region=true;valid_node=true;}
int main(void){
 struct pci_dev dev={0};struct j71s_identify_scratch s;int rc;
 reset();memset(&s,0,sizeof(s));dev.command=PCI_COMMAND_MASTER;
 if(j71s_identify_setup_scratch(&dev,bar_bytes,&s)!=-EINVAL || nwrite || s.retained)abort();
 dev.command=0;reset();allow_region=false;memset(&s,0,sizeof(s));
 if(j71s_identify_setup_scratch(&dev,bar_bytes,&s)!=-EINVAL || nwrite || s.retained || s.cpu)abort();
 for(int f=1;f<=7;f++){
  reset();fail_write=f;memset(&s,0,sizeof(s));rc=j71s_identify_setup_scratch(&dev,bar_bytes,&s);
  if(rc!=-EIO || !s.retained || s.ready || !s.cpu || !s.mmu || unmaps || nwrite<f || cache_cleans!=1)abort();
  free(s.cpu); /* Fake test process only; real hardware must retain it. */
 }
 reset();memset(&s,0,sizeof(s));rc=j71s_identify_setup_scratch(&dev,bar_bytes,&s);
 if(rc || !s.ready || !s.retained || nwrite!=7 || unmaps || cache_cleans!=1 || readl(bar_bytes+0x1810)!=J71S_SCRATCH_IOVA)abort();
 if(j71s_identify_setup_scratch(&dev,bar_bytes,&s)!=-EINVAL)abort();
 free(s.cpu);
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'test.c').write_text(preamble+fn+checks)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('Scratch setup guards, seven write failures and retention passed.')
