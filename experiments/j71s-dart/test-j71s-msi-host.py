from pathlib import Path
import subprocess,tempfile
s=(Path(__file__).parent / 'driver-patch/j71s-msi-host-test.h').read_text()
a=s.index('static int j71s_msi_alloc('); b=s.index('static const struct irq_domain_ops',a); testfunc=s[a:b]
p=r'''
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <errno.h>
typedef unsigned long irq_hw_number_t;
struct irq_fwspec {unsigned param[4];};struct irq_domain{void *host_data;};
struct j71s_msi_test{struct irq_fwspec parent_spec;int lock;unsigned long used;};
struct bus {unsigned number;};struct device {int is_pci;struct bus *bus;unsigned devfn;};
struct msi_desc {struct device *dev;};typedef struct {struct msi_desc *desc;} msi_alloc_info_t;
struct irq_data {irq_hw_number_t hwirq;};static struct irq_data data;
static int fail, parent_allocs,parent_frees, installed, last_parent;
static int dev_is_pci(struct device*d){return d->is_pci;}
#define to_pci_dev(d) (d)
#define msi_desc_to_dev(d) ((d)->dev)
#define spin_lock_irqsave(l,f) do{(void)(l);(f)=0;}while(0)
#define spin_unlock_irqrestore(l,f) do{(void)(l);(void)(f);}while(0)
static unsigned find_first_zero_bit(unsigned long *p,unsigned n){for(unsigned i=0;i<n;i++)if(!(*p&(1UL<<i)))return i;return n;}
static void __set_bit(unsigned b,unsigned long*p){*p|=1UL<<b;}
static void __clear_bit(unsigned b,unsigned long*p){*p&=~(1UL<<b);}
static int irq_domain_alloc_irqs_parent(struct irq_domain*d,unsigned v,int n,struct irq_fwspec*s){(void)d;(void)v;(void)n;last_parent=s->param[1];if(fail)return -EIO;parent_allocs++;return 0;}
static void irq_domain_free_irqs_parent(struct irq_domain*d,unsigned v,unsigned n){(void)d;(void)v;(void)n;parent_frees++;}
static int j71s_msi_chip;
static void irq_domain_set_hwirq_and_chip(struct irq_domain*d,unsigned v,unsigned h,int*c,void*ctx){(void)d;(void)v;(void)c;(void)ctx;data.hwirq=h;installed++;}
static struct irq_data *irq_domain_get_irq_data(struct irq_domain*d,unsigned v){(void)d;(void)v;return &data;}
'''
t=r'''
int main(void){struct j71s_msi_test c={.parent_spec.param={0,80}};struct irq_domain dom={&c};struct bus b={1};struct device dev={1,&b,0};struct msi_desc desc={&dev};msi_alloc_info_t info={&desc};
 if(j71s_msi_alloc(&dom,7,1,&info)||c.used!=1||last_parent!=80||data.hwirq||installed!=1)abort();
 j71s_msi_free(&dom,7,1);if(c.used||parent_frees!=1)abort();
 fail=1;if(j71s_msi_alloc(&dom,7,1,&info)!=-EIO||c.used)abort();fail=0;
 if(j71s_msi_alloc(&dom,7,2,&info)!=-ENOSPC||c.used)abort();
 c.used=255;if(j71s_msi_alloc(&dom,7,1,&info)!=-ENOSPC)abort();
 c.used=0;dev.devfn=1;if(j71s_msi_alloc(&dom,7,1,&info)!=-ENOSPC||c.used)abort();
}
'''
with tempfile.TemporaryDirectory() as d:
 pth=Path(d);(pth/'t.c').write_text(p+testfunc+t)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(pth/'t.c'),'-o',str(pth/'t')],check=True)
 subprocess.run([str(pth/'t')],check=True)
print('MSI domain allocation, rollback, routing and free checks passed.')
