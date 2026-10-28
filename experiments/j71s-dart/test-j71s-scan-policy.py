from pathlib import Path
import subprocess,tempfile
s=(Path(__file__).parent / 'driver-patch/j71s-pci-scan.h').read_text()
s=s[s.index('struct j71s_scan_state'):s.index('static struct pci_ops')]
p=r'''
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
typedef uint32_t u32;
#define __iomem
#define PCIBIOS_SET_FAILED 0x88
struct resource { int unused; };
struct pci_bus { void *sysdata; unsigned int number; };
'''
t=r'''
int main(void) {
 unsigned char mem[0x200000];struct j71s_scan_state state={mem,{0}};struct pci_bus bus={&state,0};
 if(j71s_scan_map_bus(&bus,0,0x100)!=mem+0x100)abort();
 bus.number=1;if(j71s_scan_map_bus(&bus,0,8)!=mem+0x100008)abort();
 if(j71s_scan_map_bus(&bus,8,8)||j71s_scan_map_bus(&bus,0,-1)||j71s_scan_map_bus(&bus,0,0x1000))abort();
 bus.number=2;if(j71s_scan_map_bus(&bus,0,0))abort();
 if(j71s_scan_no_write(&bus,0,4,2,4)!=PCIBIOS_SET_FAILED)abort();
 return 0;
}
'''
with tempfile.TemporaryDirectory() as d:
 pth=Path(d);(pth/'t.c').write_text(p+s+t)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Wno-unused-parameter','-Werror',str(pth/'t.c'),'-o',str(pth/'t')],check=True)
 subprocess.run([str(pth/'t')],check=True)
print('PCI configuration mapping limits and write-denial policy passed.')
