from pathlib import Path
import subprocess,tempfile
s=(Path(__file__).parent / 'driver-patch/j71s-pci-driver-test.h').read_text()
s=s[s.index('struct j71s_scan_state'):s.index('static struct pci_ops')]
p=r'''
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
typedef uint32_t u32;
#define __iomem
#define U32_MAX UINT32_MAX
#define PCI_BASE_ADDRESS_0 0x10
#define PCI_BASE_ADDRESS_1 0x14
#define PCI_COMMAND 4
#define PCI_COMMAND_MEMORY 2
#define PCI_COMMAND_MASTER 4
#define PCIBIOS_SET_FAILED 0x88
struct resource { int unused; };
struct pci_bus { void *sysdata; unsigned int number; };
static int allowed;
static u32 readl(void *p){u32 v;memcpy(&v,p,4);return v;}
static uint16_t readw(void *p){uint16_t v;memcpy(&v,p,2);return v;}
static int pci_generic_config_write(struct pci_bus *bus,unsigned devfn,int where,int size,u32 value) {(void)bus;(void)devfn;(void)where;(void)size;(void)value;allowed++;return 0;}
'''
t=r'''
int main(void) {
 static unsigned char mem[0x200000];
 struct j71s_scan_state state={mem,{0},{0},0};
 struct pci_bus bus={&state,1};
 u32 id=0x2002106b;
 if(j71s_scan_map_bus(&bus,0,4)!=mem+0x100004)abort();
 memcpy(mem+0x100000,&id,4);
 if(j71s_scan_bar_write(&bus,0,PCI_COMMAND,2,PCI_COMMAND_MEMORY))abort();
 if(j71s_scan_bar_write(&bus,0,PCI_COMMAND,2,0))abort();
 /* ANS preinit needs these writes; this read-only host deliberately rejects them. */
 if(j71s_scan_bar_write(&bus,0,0x0d,1,0x40)!=PCIBIOS_SET_FAILED ||
    j71s_scan_bar_write(&bus,0,0x17c,4,0)!=PCIBIOS_SET_FAILED ||
    j71s_scan_bar_write(&bus,0,0x18c,4,0)!=PCIBIOS_SET_FAILED ||
    j71s_scan_bar_write(&bus,0,0x188,4,0)!=PCIBIOS_SET_FAILED ||
    j71s_scan_bar_write(&bus,0,PCI_COMMAND,2,PCI_COMMAND_MEMORY|PCI_COMMAND_MASTER)!=PCIBIOS_SET_FAILED)abort();
 bus.number=0;
 if(j71s_scan_bar_write(&bus,0,PCI_COMMAND,2,PCI_COMMAND_MEMORY)!=PCIBIOS_SET_FAILED)abort();
 if(allowed!=2)abort();
 return 0;
}
'''
with tempfile.TemporaryDirectory() as d:
 pth=Path(d);(pth/'t.c').write_text(p+s+t)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(pth/'t.c'),'-o',str(pth/'t')],check=True)
 subprocess.run([str(pth/'t')],check=True)
print('PCI diagnostic policy rejects ANS setup and bus mastering as expected.')
