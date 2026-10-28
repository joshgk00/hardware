from pathlib import Path
import subprocess,tempfile
s=(Path(__file__).parent / 'driver-patch/j71s-pci-iomap.h').read_text()
a=s.index('static int j71s_pcie_test_iomap(');b=s.index('static int j71s_pcie_scan_once(',a);s=s[a:b]
p=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
typedef uint16_t u16;typedef uint32_t u32;
#define __iomem
#define PCI_COMMAND 4
#define PCI_COMMAND_MEMORY 2
#define PCI_COMMAND_MASTER 4
struct device { int dummy; };struct pci_dev { int dummy; };
struct j71s_scan_state { unsigned char *ecam; };
static unsigned char mmio[0x4000]; static int mapfail,block_root,block_ep,maps,unmaps;
static u32 readl(void*p){u32 v;memcpy(&v,p,4);return v;}
static u16 readw(void*p){u16 v;memcpy(&v,p,2);return v;}
static unsigned char *base;
static void writew(u16 v,void*p){if ((v&2)&&((block_root && p==base+4)||(block_ep && p==base+0x100004))) return;memcpy(p,&v,2);}
static void *pci_iomap(struct pci_dev*d,int bar,int max){(void)d;(void)bar;(void)max;maps++;return mapfail?NULL:mmio;}
static void pci_iounmap(struct pci_dev*d,void*p){(void)d;(void)p;unmaps++;}
#define dev_info(...) ((void)0)
'''
t=r'''
static void check(int x){if(!x)abort();}
int main(void){static unsigned char ecam[0x200000];struct j71s_scan_state s={ecam};struct device d;struct pci_dev e;u32 v;
 base=ecam;v=0xc0000004;memcpy(ecam+0x100010,&v,4);v=0x10001;memcpy(mmio+8,&v,4);
 check(j71s_pcie_test_iomap(&d,&s,&e)==0 && maps==1 && unmaps==1 && !readw(ecam+4) && !readw(ecam+0x100004));
 mapfail=1;check(j71s_pcie_test_iomap(&d,&s,&e)==-ENOMEM && unmaps==1);mapfail=0;
 block_root=1;check(j71s_pcie_test_iomap(&d,&s,&e)==-EIO && unmaps==2 && !readw(ecam+4));block_root=0;
 block_ep=1;check(j71s_pcie_test_iomap(&d,&s,&e)==-EIO && unmaps==3 && !readw(ecam+4) && !readw(ecam+0x100004));block_ep=0;
 ecam[0x100004]=4;check(j71s_pcie_test_iomap(&d,&s,&e)==-EINVAL && maps==4);
}
'''
with tempfile.TemporaryDirectory() as d:
 pth=Path(d);(pth/'t.c').write_text(p+s+t)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Wno-unused-parameter','-Werror',str(pth/'t.c'),'-o',str(pth/'t')],check=True)
 subprocess.run([str(pth/'t')],check=True)
print('PCI mapping and decode guard/restore cases passed.')
