from pathlib import Path
import subprocess,tempfile
src=(Path(__file__).parent / 'driver-patch/j71s-ans-config-policy.h').read_text()
state=src[src.index('struct j71s_scan_state'):src.index('static int j71s_scan_bar_write')]
a=src.index('static int j71s_scan_bar_write(');fn=src[a:]
p=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
typedef uint32_t u32; typedef uint16_t u16; typedef uint8_t u8;
#define __iomem
#define U32_MAX UINT32_MAX
#define PCI_COMMAND 4
#define PCI_COMMAND_MEMORY 2
#define PCI_COMMAND_MASTER 4
#define PCI_COMMAND_INTX_DISABLE 0x400
#define PCI_MSI_FLAGS_ENABLE 1
#define PCI_MSI_FLAGS_QSIZE 0x70
#define PCI_BASE_ADDRESS_0 0x10
#define PCI_BASE_ADDRESS_1 0x14
#define PCIBIOS_SET_FAILED 0x88
#define J71S_TEST_MSI_DOORBELL 0xbffff000ULL
#define lower_32_bits(x) ((u32)(x))
#define upper_32_bits(x) ((u32)((x)>>32))
struct resource {int x;};struct pci_bus {void *sysdata;unsigned number;};
static int writes;
static u32 readl(void*p){u32 v;memcpy(&v,p,4);return v;}
static u16 readw(void*p){u16 v;memcpy(&v,p,2);return v;}
static int pci_generic_config_write(struct pci_bus*b,unsigned d,int w,int s,u32 v){(void)b;(void)d;(void)w;(void)s;(void)v;writes++;return 0;}
'''
t=r'''
int main(void){static unsigned char mem[0x200000];struct j71s_scan_state st={.ecam=mem,.msi_active=true,.msi_ctrl=0x86,.msi_lo=0x1234,.msi_hi=5,.msi_data=9};struct pci_bus bus={&st,1};u32 id=0x2002106b;memcpy(mem+0x100000,&id,4);
 if(j71s_scan_bar_write(&bus,0,0x52,2,0x87)||j71s_scan_bar_write(&bus,0,0x54,4,0xbffff000)||j71s_scan_bar_write(&bus,0,0x58,4,0)||j71s_scan_bar_write(&bus,0,0x5c,2,0)||j71s_scan_bar_write(&bus,0,4,2,0x402))abort();
 if(j71s_scan_bar_write(&bus,0,4,2,6)!=PCIBIOS_SET_FAILED || j71s_scan_bar_write(&bus,0,0x54,4,0xdeadbeef)!=PCIBIOS_SET_FAILED || j71s_scan_bar_write(&bus,0,0x5c,2,3)!=PCIBIOS_SET_FAILED || j71s_scan_bar_write(&bus,0,0x52,2,0x887)!=PCIBIOS_SET_FAILED)abort();
 st.msi_active=false;if(j71s_scan_bar_write(&bus,0,0x52,2,0x87)!=PCIBIOS_SET_FAILED)abort();
 st.msi_active=true;mem[0x100004]=4;if(j71s_scan_bar_write(&bus,0,0x54,4,0xbffff000)!=PCIBIOS_SET_FAILED)abort();mem[0x100004]=0; st.ans_cfg_active=true;st.ans_latency=0x22;st.ans_ltr=0x11111111;st.ans_ctl2=0x22222222;st.ans_ctl1=0x33333333;
 if(j71s_scan_bar_write(&bus,0,0x17c,4,0x10081008)||j71s_scan_bar_write(&bus,0,0x18c,4,0)||j71s_scan_bar_write(&bus,0,0x188,4,0x40440000))abort();
 if(j71s_scan_bar_write(&bus,0,0x188,4,0x40550000)!=PCIBIOS_SET_FAILED||j71s_scan_bar_write(&bus,0,0x17c,4,0xdeadbeef)!=PCIBIOS_SET_FAILED||j71s_scan_bar_write(&bus,0,4,2,6)!=PCIBIOS_SET_FAILED)abort();
 st.ans_cfg_active=false;if(j71s_scan_bar_write(&bus,0,0x188,4,0x40440000)!=PCIBIOS_SET_FAILED)abort();if(writes!=8)abort();
}
'''
with tempfile.TemporaryDirectory() as d:
 pth=Path(d);(pth/'t.c').write_text(p+state+fn+t)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(pth/'t.c'),'-o',str(pth/'t')],check=True)
 subprocess.run([str(pth/'t')],check=True)
print('MSI and ANS config policy restricts candidate and restore writes.')
