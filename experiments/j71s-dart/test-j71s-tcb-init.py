from pathlib import Path
import subprocess,tempfile
s=(Path(__file__).parent / 'driver-patch/j71s-tcb-init-test.h').read_text();s=s[s.index('static bool j71s_dma_is_identity'):]
p=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <stdarg.h>
typedef uint16_t u16;typedef uint32_t u32;typedef uint64_t u64;typedef uint64_t dma_addr_t;
#define __iomem
#define PAGE_SIZE 16384
#define PAGE_ALIGN(x) (((x)+PAGE_SIZE-1)&~(PAGE_SIZE-1))
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
#define PCI_COMMAND 4
#define PCI_COMMAND_MASTER 4
#define SZ_4K 4096
#define U32_MAX UINT32_MAX
#define IS_ALIGNED(x,a) (((x)&((a)-1))==0)
#define DMA_BIT_MASK(x) (UINT64_MAX>>(64-(x)))
#define GFP_KERNEL 0
#define __GFP_ZERO 0
#define lower_32_bits(x) ((u32)(x))
#define upper_32_bits(x) ((u32)((x)>>32))
#define dma_wmb() ((void)0)
#define dma_rmb() ((void)0)
static void *memchr_inv(const void*p,int c,size_t n){const unsigned char *b=p;for(size_t i=0;i<n;i++)if(b[i]!=(unsigned char)c)return (void*)(b+i);return NULL;}
struct device{u64*dma_mask;u64 coherent_dma_mask;};struct pci_dev{int dummy;};
struct scatterlist{size_t length;dma_addr_t phys;};struct sg_table{unsigned nents;struct scatterlist *sgl;};
static unsigned char mmio[0x1000];static struct scatterlist sg;static void *buffers[2];static int mode,allocs,frees,writes,armed,sg_frees,report_tcb,report_table;
static bool j71s_test_kexec_locked(void){return mode!=1;}
static void *iommu_get_domain_for_dev(struct device*d){(void)d;return mode==2?(void*)1:NULL;}
static int pci_read_config_word(struct pci_dev*p,int o,u16*v){(void)p;(void)o;*v=mode==3?4:0;return 0;}
static int dma_set_mask(struct device*d,u64 m){*d->dma_mask=m;return 0;}
static int dma_set_coherent_mask(struct device*d,u64 m){d->coherent_dma_mask=m;return 0;}
static void *dma_alloc_coherent(struct device*d,size_t n,dma_addr_t*a,int f){(void)d;(void)f;allocs++;if(mode==4&&allocs==2)return NULL;*a=allocs==1?0x100000:0x200000;buffers[allocs-1]=calloc(1,n);return buffers[allocs-1];}
static void dma_free_coherent(struct device*d,size_t n,void*p,dma_addr_t a){(void)d;(void)n;(void)a;frees++;free(p);}
static int dma_get_sgtable(struct device*d,struct sg_table*t,void*p,dma_addr_t a,size_t n){(void)d;(void)p;sg.length=n;sg.phys=mode==5?a+4096:a;t->nents=1;t->sgl=&sg;return 0;}
static dma_addr_t sg_phys(struct scatterlist*s){return s->phys;}
static void sg_free_table(struct sg_table*t){(void)t;sg_frees++;}
static void *ioremap(u64 a,int n){(void)a;(void)n;return mmio;}
static void iounmap(void*p){(void)p;}
static u32 readl(void*p){u32 v;memcpy(&v,p,4);return v;}
static void writel(u32 v,void*p){long off=(unsigned char*)p-mmio;writes++;if(mode==6&&off==8&&v)return;if(off==4&&v==0x10000){armed++;if(mode==8){((char*)buffers[0])[0]=1;((char*)buffers[1])[0]=1;}v=mode==7?0x10000:0;}memcpy(p,&v,4);}
#define readl_poll_timeout(addr,val,cond,delay,timeout) ((void)(delay),(void)(timeout),(val)=readl(addr),(cond)?0:-ETIMEDOUT)
static void dev_info(struct device *d,const char *fmt,...){(void)d;if(strstr(fmt,"armed=1 poll=")){va_list a;va_start(a,fmt);for(int i=0;i<5;i++)(void)va_arg(a,int);report_tcb=va_arg(a,int);report_table=va_arg(a,int);va_end(a);}}
'''
t=r'''
int main(void){u64 mask=0xffffffff;struct device d={&mask,0xffffffff};struct pci_dev p={0};unsigned char bar[64]={0};
 for(mode=0;mode<=8;mode++){memset(mmio,0,sizeof(mmio));allocs=frees=writes=armed=sg_frees=report_tcb=report_table=0;mask=d.coherent_dma_mask=0xffffffff;j71s_test_tcb_init(&p,bar,&d);
  if(mode==0 && (armed!=1||frees||allocs!=2||sg_frees!=2))abort();
  if(mode>=1&&mode<=3 && (armed||allocs))abort();
  if(mode==4 && (armed||frees!=1||writes))abort();
  if(mode==5 && (armed||frees!=2||writes))abort();
  if(mode==6 && (armed||frees!=2))abort();
  if(mode==7 && (armed!=1||frees||allocs!=2))abort();
  if(mode==8 && (armed!=1||frees||!report_tcb||!report_table))abort();
 }
}
'''
with tempfile.TemporaryDirectory() as d:
 pth=Path(d);(pth/'t.c').write_text(p+s+t)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(pth/'t.c'),'-o',str(pth/'t')],check=True)
 subprocess.run([str(pth/'t')],check=True)
print('One-shot TCB init, identity-DMA guards and retained-buffer paths passed.')
