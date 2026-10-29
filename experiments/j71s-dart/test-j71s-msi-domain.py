from pathlib import Path
import subprocess,tempfile
s=(Path(__file__).parent / 'driver-patch/j71s-msi-domain-test.h').read_text();s=s[s.index('static int j71s_test_aic_vectors'):]
p=r'''
#include <stdint.h>
#include <errno.h>
#include <stdlib.h>
typedef uint32_t u32;
#define U32_MAX UINT32_MAX
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
#define AIC_IRQ 0
#define IRQ_TYPE_EDGE_RISING 1
#define DOMAIN_BUS_WIRED 0
struct device{int dummy;}; struct device_node{int dummy;};
struct irq_fwspec{void*fwnode;unsigned param_count;u32 param[4];};
struct irq_domain; struct irq_domain_ops{int(*translate)(struct irq_domain*,struct irq_fwspec*,unsigned long*,unsigned*);};
struct irq_domain{struct irq_domain_ops*ops;};
static int existing=-1, fail_at=-1, allocs, disposals, puts;
static struct device_node node;
static int translate(struct irq_domain*d,struct irq_fwspec*s,unsigned long*h,unsigned*t){(void)d;*h=s->param[1];*t=1;return 0;}
static struct irq_domain_ops ops={translate};static struct irq_domain dom={&ops};
static struct device_node *of_find_compatible_node(void*a,void*b,const char*c){(void)a;(void)b;(void)c;return &node;}
static void *of_fwnode_handle(struct device_node*n){return n;}
static struct irq_domain *irq_find_matching_fwspec(struct irq_fwspec*s,int t){(void)s;(void)t;return &dom;}
static int irq_find_mapping(struct irq_domain*d,unsigned long h){(void)d;return (int)h==existing;}
static unsigned irq_create_fwspec_mapping(struct irq_fwspec*s){if((int)s->param[1]==fail_at)return 0;allocs++;return s->param[1]+100;}
static void irq_dispose_mapping(unsigned i){(void)i;disposals++;}
static void of_node_put(struct device_node*n){(void)n;puts++;}
#define dev_info(...) ((void)dev)
'''
t=r'''
int main(void){struct device d={0};
 if(j71s_test_aic_vectors(&d,80,8)||allocs!=8||disposals!=8||puts!=1)abort();
 allocs=disposals=puts=0; existing=83;if(j71s_test_aic_vectors(&d,80,8)!=-EBUSY||allocs!=3||disposals!=3||puts!=1)abort();
 allocs=disposals=puts=0;existing=-1;fail_at=82;if(j71s_test_aic_vectors(&d,80,8)!=-ENOSPC||allocs!=2||disposals!=2)abort();
 allocs=disposals=puts=0;if(j71s_test_aic_vectors(&d,80,9)!=-EINVAL||allocs||puts)abort();
}
'''
with tempfile.TemporaryDirectory() as d:
 pth=Path(d);(pth/'t.c').write_text(p+s+t)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(pth/'t.c'),'-o',str(pth/'t')],check=True)
 subprocess.run([str(pth/'t')],check=True)
print('AIC vector mapping, conflict and partial cleanup checks passed.')
