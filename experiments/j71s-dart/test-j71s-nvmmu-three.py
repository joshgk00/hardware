from pathlib import Path
import subprocess,tempfile
s=(Path(__file__).parent / 'driver-patch/j71s-nvmmu-three-fields.h').read_text();s=s[s.index('static void j71s_test_nvmmu_window'):]
p=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
typedef uint16_t u16;typedef uint32_t u32;typedef uint64_t u64;
#define __iomem
#define U32_MAX UINT32_MAX
#define BIT(x) (1U << (x))
#define PCI_COMMAND 4
#define PCI_COMMAND_MASTER 4
#define IORESOURCE_SYSTEM_RAM 1
#define IORES_DESC_NONE 0
#define REGION_DISJOINT 0
#define IS_ALIGNED(x,a) (((x)&((a)-1))==0)
struct device {int n;}; struct pci_dev {struct device dev;};struct device_node {int n;};struct reserved_mem {u64 base,size;};
static struct device_node node;static struct reserved_mem region={0x800000000ULL,0xe00000};
static unsigned char mmu[4096],bar[0x100];static int command,maps,writes,failwrite=-1,errors,matched=-1,remaining=-1;
static struct device_node *of_find_node_by_path(const char *p){(void)p;return &node;}
static struct reserved_mem *of_reserved_mem_lookup(struct device_node*n){(void)n;return &region;}
static int of_property_read_bool(struct device_node*n,const char *p){(void)n;return !strcmp(p,"no-map");}
static int region_intersects(u64 b,u64 sz,int f,int d){(void)b;(void)sz;(void)f;(void)d;return 0;}
static int pci_read_config_word(struct pci_dev*p,int where,u16*v){(void)p;(void)where;*v=command;return 0;}
static void *ioremap(u64 b,u64 sz){(void)b;(void)sz;maps++;return mmu;}
static void iounmap(void*p){(void)p;}
static u32 readl(void*p){u32 v;memcpy(&v,p,4);return v;}
static void writel(u32 v,void*p){int idx=writes++; if((unsigned char*)p<mmu+0x24||(unsigned char*)p>mmu+0x2c||readl(mmu+0x20))abort();if(idx!=failwrite){if(p==mmu+0x24||p==mmu+0x28)v|=BIT(31);memcpy(p,&v,4);}}
static void of_node_put(struct device_node*n){(void)n;}
static void dev_info(struct device*d,const char*fmt,...){(void)d;if(strstr(fmt,"private NVMMU") || strstr(fmt,"NVMMU field:")) return;va_list a;va_start(a,fmt);matched=va_arg(a,int);(void)va_arg(a,int);errors=va_arg(a,unsigned);remaining=va_arg(a,unsigned);va_end(a);}
'''
t=r'''
static void reset(void){memset(mmu,0,sizeof(mmu));memset(bar,0,sizeof(bar));u32 a=0x80000111,b=0x80000222,c=0x333;memcpy(mmu+0x24,&a,4);memcpy(mmu+0x28,&b,4);memcpy(mmu+0x2c,&c,4);command=maps=writes=errors=remaining=0;matched=-1;failwrite=-1;}
int main(void){struct pci_dev p;reset();j71s_test_nvmmu_window(&p,bar);if(!matched||errors||remaining||writes!=6||readl(mmu+0x24)!=0x80000111||readl(mmu+0x28)!=0x80000222||readl(mmu+0x2c)!=0x333)abort();
 reset();command=4;j71s_test_nvmmu_window(&p,bar);if(maps||writes)abort();
 reset();u32 one=1;memcpy(mmu+0x20,&one,4);j71s_test_nvmmu_window(&p,bar);if(writes)abort();
 reset();failwrite=1;j71s_test_nvmmu_window(&p,bar);if(matched||errors||remaining||writes!=4||readl(mmu+0x24)!=0x80000111||readl(mmu+0x28)!=0x80000222)abort();
}
'''
with tempfile.TemporaryDirectory() as d:
 pth=Path(d);(pth/'t.c').write_text(p+s+t)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(pth/'t.c'),'-o',str(pth/'t')],check=True)
 subprocess.run([str(pth/'t')],check=True)
print('NVMMU disabled-control, DMA guards, failure and restoration tests passed.')
