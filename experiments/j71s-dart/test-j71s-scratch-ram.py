from pathlib import Path
import subprocess,tempfile
s=(Path(__file__).parent / 'driver-patch/j71s-scratch-test.h').read_text();s=s[s.index('static void j71s_test_reserved_scratch'):]
p=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
typedef uint32_t u32;typedef uint64_t u64;
#define __iomem
#define U32_MAX UINT32_MAX
#define IORESOURCE_SYSTEM_RAM 1
#define IORES_DESC_NONE 0
#define REGION_DISJOINT 0
#define MEMREMAP_WB 1
#define READ_ONCE(x) (x)
#define WRITE_ONCE(x,v) ((x)=(v))
#define IS_ALIGNED(x,a) (((x)&((a)-1))==0)
#define mb() ((void)0)
struct device {int n;}; struct device_node {int n;};struct reserved_mem {u64 base,size;};
static struct device_node node;static struct reserved_mem region={0x800000000ULL,0xe00000};
static unsigned char *mem;static unsigned char mmu[4096];static int allow=1, overlap=0, failmap=0, maps, unmaps;
static struct device_node *of_find_node_by_path(const char *p){(void)p;return allow?&node:NULL;}
static struct reserved_mem *of_reserved_mem_lookup(struct device_node*n){(void)n;return &region;}
static int of_property_read_bool(struct device_node*n,const char *p){(void)n;return !strcmp(p,"no-map");}
static int region_intersects(u64 b,u64 sz,int f,int d){(void)b;(void)sz;(void)f;(void)d;return overlap;}
static void *memremap(u64 b,u64 sz,int f){(void)b;(void)sz;(void)f;maps++;return failmap?NULL:mem;}
static void memunmap(void *p){if(p!=mem)abort();unmaps++;}
static void of_node_put(struct device_node*n){(void)n;}
static void *ioremap(u64 b,u64 s){(void)b;(void)s;return mmu;}
static void iounmap(void*p){(void)p;}
static u32 readl(void*p){u32 v;memcpy(&v,p,4);return v;}
static void dev_info(struct device*d,const char*fmt,...){(void)d;(void)fmt;}
'''
t=r'''
int main(void) {struct device d;mem=malloc(region.size);if(!mem)abort();memset(mem,0x5a,region.size);
 j71s_test_reserved_scratch(&d);if(maps!=1 || unmaps!=1 || mem[0]!=0x5a || mem[region.size/2]!=0x5a || mem[region.size-1]!=0x5a)abort();
 overlap=1;j71s_test_reserved_scratch(&d);if(maps!=1)abort();overlap=0;
 region.size=4096;j71s_test_reserved_scratch(&d);if(maps!=1)abort();region.size=0xe00000;
 failmap=1;j71s_test_reserved_scratch(&d);if(maps!=2 || unmaps!=1)abort();
 allow=0;j71s_test_reserved_scratch(&d);if(maps!=2)abort();j71s_observe_nvmmu(&d);free(mem);
}
'''
with tempfile.TemporaryDirectory() as d:
 pth=Path(d);(pth/'t.c').write_text(p+s+t)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(pth/'t.c'),'-o',str(pth/'t')],check=True)
 subprocess.run([str(pth/'t')],check=True)
print('Scratch mapping, restoration, reservation guards and read-only MMU observation passed.')
