from pathlib import Path
import subprocess,tempfile
s=(Path(__file__).parent / 'driver-patch/j71s-tcb-address-test.h').read_text();s=s[s.index('static void j71s_test_tcb_addresses'):]
p=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
typedef uint16_t u16;typedef uint32_t u32;typedef uint64_t u64;typedef uint64_t dma_addr_t;
#define __iomem
#define U32_MAX UINT32_MAX
#define PAGE_SIZE 16384
#define PAGE_ALIGN(x) (((x)+PAGE_SIZE-1)&~(PAGE_SIZE-1))
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
#define PCI_COMMAND 4
#define PCI_COMMAND_MASTER 4
#define SZ_4K 4096
#define IS_ALIGNED(x,a) (((x)&((a)-1))==0)
#define DMA_BIT_MASK(x) UINT64_MAX
#define GFP_KERNEL 0
#define __GFP_ZERO 0
#define lower_32_bits(x) ((u32)(x))
#define upper_32_bits(x) ((u32)((x)>>32))
#define dma_wmb() ((void)0)
struct device{u64*dma_mask;u64 coherent_dma_mask;};struct pci_dev{int dummy;};
static unsigned char mmio[0x1000];static int mode,allocs,frees,writes,report_retained,report_errors,report_matched;
static int pci_read_config_word(struct pci_dev*p,int o,u16*v){(void)p;(void)o;*v=mode==1?4:0;return 0;}
static int dma_set_mask(struct device*d,u64 m){*d->dma_mask=m;return 0;}
static int dma_set_coherent_mask(struct device*d,u64 m){d->coherent_dma_mask=m;return 0;}
static void *dma_alloc_coherent(struct device*d,size_t n,dma_addr_t*a,int f){(void)d;(void)f;allocs++;if(mode==2&&allocs==2)return NULL;*a=allocs==1?0x100000:0x200000;return calloc(1,n);}
static void dma_free_coherent(struct device*d,size_t n,void*p,dma_addr_t a){(void)d;(void)n;(void)a;frees++;free(p);}
static void *ioremap(u64 a,int n){(void)a;(void)n;return mmio;}
static void iounmap(void*p){(void)p;}
static u32 readl(void*p){u32 v;memcpy(&v,p,4);return v;}
static void writel(u32 v,void*p){long off=(unsigned char*)p-mmio;writes++;if(mode==3&&off==8&&v)return;if(mode==4&&off==0x10&&!v)return;memcpy(p,&v,4);}
static void dev_info(struct device*d,const char*fmt,...){(void)d;if(strstr(fmt,"matched=%d")){__builtin_va_list a;__builtin_va_start(a,fmt);report_matched=__builtin_va_arg(a,int);report_errors=__builtin_va_arg(a,unsigned);report_retained=__builtin_va_arg(a,int);__builtin_va_end(a);}}
'''
t=r'''
int main(void){u64 mask=0xffffffff;struct device d={&mask,0xffffffff};struct pci_dev p={0};unsigned char bar[64]={0};
 for(mode=0;mode<=6;mode++){memset(mmio,0,sizeof(mmio));allocs=frees=writes=report_retained=report_errors=report_matched=0;mask=d.coherent_dma_mask=0xffffffff;
  if(mode==5){u32 a=0x1234,b=0x5678;memcpy(mmio+0x10,&a,4);memcpy(mmio+0x14,&b,4);}
  if(mode==6){u32 a=U32_MAX;memcpy(mmio+0x10,&a,4);}
  j71s_test_tcb_addresses(&p,bar,&d);
  if(mode==0 && (allocs!=2||frees!=2||writes!=8||!report_matched||report_errors||report_retained||mask!=0xffffffff))abort();
  if(mode==1 && allocs)abort();
  if(mode==2 && (allocs!=2||frees!=1||writes))abort();
  if(mode==3 && (frees!=2||report_matched||report_retained))abort();
  if(mode==4 && (frees||!report_retained||!report_errors))abort();
  if(mode==5 && (frees!=2||!report_matched||report_retained||readl(mmio+0x10)!=0x1234||readl(mmio+0x14)!=0x5678))abort();
  if(mode==6 && (frees!=2||writes))abort();
 }
}
'''
with tempfile.TemporaryDirectory() as d:
 pth=Path(d);(pth/'t.c').write_text(p+s+t)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(pth/'t.c'),'-o',str(pth/'t')],check=True)
 subprocess.run([str(pth/'t')],check=True)
print('TCB address programming, restoration and retained-buffer guards passed.')
