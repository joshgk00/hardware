#!/usr/bin/env python3
"""Test the actual ANS PCI config helper from the experimental patch."""
from pathlib import Path
import subprocess,tempfile
s=Path(__file__).with_name('j71s-ans-pci-config.patch').read_text()
added='\n'.join(x[1:] for x in s.splitlines() if x.startswith('+') and not x.startswith('+++'))
a=added.index('static int apple_ans_configure_pci(');b=added.index('\n}',a)+2
helper=added[a:b]
p=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <errno.h>
typedef uint16_t u16;typedef uint32_t u32;
#define PCI_EXT_CAP_ID_LTR 0x18
#define PCI_EXT_CAP_ID_L1SS 0x1e
#define PCI_LATENCY_TIMER 0x0d
#define PCI_LTR_MAX_SNOOP_LAT 4
#define PCI_L1SS_CTL1 8
#define PCI_L1SS_CTL2 12
#define PCIBIOS_SUCCESSFUL 0
#define APPLE_ANS_LTR_VALUE 0x10081008
#define APPLE_ANS_L1SS_T8010 0x40550000
#define APPLE_ANS_L1SS_S8000_CANDIDATE 0x40440000
struct pci_dev{int x;};static int mode,fail,used,offs[4];static u32 vals[4];
static u16 pci_find_ext_capability(struct pci_dev*p,int cap){(void)p;if(mode==1&&cap==PCI_EXT_CAP_ID_LTR)return 0;if(mode==2&&cap==PCI_EXT_CAP_ID_L1SS)return 0;return cap==PCI_EXT_CAP_ID_LTR?0x200:0x300;}
static int record(int off,u32 v){offs[used]=off;vals[used]=v;used++;return used==fail?-1:0;}
static int pci_write_config_byte(struct pci_dev*p,int off,int v){(void)p;return record(off,v);}
static int pci_write_config_dword(struct pci_dev*p,int off,u32 v){(void)p;return record(off,v);}
'''
t=r'''
int main(void){struct pci_dev p={0};
 for(int variant=0;variant<2;variant++) {mode=fail=used=0;if(apple_ans_configure_pci(&p,variant)||used!=4||offs[0]!=0xd||offs[1]!=0x204||offs[2]!=0x30c||offs[3]!=0x308||vals[3]!=(variant?0x40440000:0x40550000))abort();}
 for(mode=1;mode<=2;mode++){fail=used=0;if(apple_ans_configure_pci(&p,1)!=-ENODEV||used)abort();}
 mode=0;for(fail=1;fail<=4;fail++){used=0;if(apple_ans_configure_pci(&p,1)!=-EIO||used!=fail)abort();}
}
'''
with tempfile.TemporaryDirectory() as d:
 pth=Path(d);(pth/'t.c').write_text(p+helper+t)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(pth/'t.c'),'-o',str(pth/'t')],check=True)
 subprocess.run([str(pth/'t')],check=True)
print('ANS PCI capability discovery, variant settings and failure handling passed.')
