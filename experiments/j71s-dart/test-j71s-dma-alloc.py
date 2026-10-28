from pathlib import Path
import subprocess,tempfile
s=(Path(__file__).parent / 'driver-patch/j71s-dma-alloc-test.h').read_text();s=s[s.index('static void j71s_test_dma_allocations'):]
p=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
typedef uint16_t u16;typedef uint32_t u32;typedef uint64_t u64;typedef uint64_t dma_addr_t;
#define __iomem
#define PCI_COMMAND 4
#define PCI_COMMAND_MASTER 4
#define PAGE_SIZE 16384
#define PAGE_ALIGN(x) (((x)+PAGE_SIZE-1)&~(PAGE_SIZE-1))
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
#define SZ_4K 4096
#define IS_ALIGNED(x,a) (((x)&((a)-1))==0)
#define DMA_BIT_MASK(x) UINT64_MAX
#define GFP_KERNEL 0
#define WRITE_ONCE(x,v) ((x)=(v))
#define READ_ONCE(x) (x)
#define dma_wmb() ((void)0)
struct device {u64 *dma_mask;u64 coherent_dma_mask;};struct pci_dev {struct device dev;};
static int command, allocs, frees, fail_at=-1, fail_coherent, report_alloc, report_aligned, report_pattern, report_restore;
static int pci_read_config_word(struct pci_dev*p,int where,u16*v){(void)p;(void)where;*v=command;return 0;}
static u32 readl(void*p){u32 v;memcpy(&v,p,4);return v;}
static int dma_set_mask(struct device*d,u64 m){*d->dma_mask=m;return 0;}
static int dma_set_coherent_mask(struct device*d,u64 m){if(fail_coherent && m==UINT64_MAX)return -1;d->coherent_dma_mask=m;return 0;}
static void *dma_alloc_coherent(struct device*d,size_t n,dma_addr_t*a,int f){(void)d;(void)f;int i=allocs++;if(i==fail_at)return NULL;*a=0x100000ULL+i*0x100000ULL;return malloc(n);}
static void dma_free_coherent(struct device*d,size_t n,void*p,dma_addr_t a){(void)d;(void)n;(void)a;frees++;free(p);}
static void dev_info(struct device*d,const char*fmt,...){(void)d;if(!strstr(fmt,"allocated=%u"))return;va_list a;va_start(a,fmt);report_alloc=va_arg(a,unsigned);report_aligned=va_arg(a,int);report_pattern=va_arg(a,int);report_restore=va_arg(a,int);va_end(a);}
'''
t=r'''
static void reset(void){command=allocs=frees=fail_coherent=report_alloc=report_aligned=report_pattern=report_restore=0;fail_at=-1;}
int main(void){u64 mask=0xffffffff;struct pci_dev p={{&mask,0xffffffff}};unsigned char bar[0x100]={0};
 reset();j71s_test_dma_allocations(&p,bar);if(allocs!=5||frees!=5||report_alloc!=5||!report_aligned||!report_pattern||!report_restore||mask!=0xffffffff||p.dev.coherent_dma_mask!=0xffffffff)abort();
 reset();fail_at=2;j71s_test_dma_allocations(&p,bar);if(allocs!=3||frees!=2||report_alloc!=2||!report_restore)abort();
 reset();fail_coherent=1;j71s_test_dma_allocations(&p,bar);if(allocs||frees||mask!=0xffffffff)abort();
 reset();command=4;j71s_test_dma_allocations(&p,bar);if(allocs)abort();
}
'''
with tempfile.TemporaryDirectory() as d:
 pth=Path(d);(pth/'t.c').write_text(p+s+t)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(pth/'t.c'),'-o',str(pth/'t')],check=True)
 subprocess.run([str(pth/'t')],check=True)
print('DMA allocation, partial failure, mask rollback and bus-master guard passed.')
