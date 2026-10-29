#!/usr/bin/env python3
"""Test the actual J71s inherited-state guard before PCI bus mastering."""
from pathlib import Path
import subprocess,tempfile
s=Path(__file__).with_name('j71s-nvme-master-guard.patch').read_text()
a='\n'.join(x[1:] for x in s.splitlines() if x.startswith('+') and not x.startswith('+++'))
start=a.index('static int nvme_j71s_master_guard');end=a.index('\n}',start)+2
helper=a[start:end]
p=r'''
#include <stdint.h>
#include <errno.h>
#include <stdlib.h>
#include <string.h>
typedef uint16_t u16;typedef uint32_t u32;
#define __iomem
#define PCI_COMMAND 4
#define PCI_COMMAND_MASTER 4
#define NVME_REG_CC 0x14
#define NVME_REG_CSTS 0x1c
struct pci_dev{int x;};static int command,failed,reads;
static int pci_read_config_word(struct pci_dev*p,int o,u16*v){(void)p;(void)o;*v=command;return failed;}
static u32 readl(void*p){u32 v;reads++;memcpy(&v,p,4);return v;}
'''
t=r'''
int main(void){struct pci_dev p={0};unsigned char bar[64]={0};u32 v;
 command=failed=reads=0;if(nvme_j71s_master_guard(&p,bar)||reads!=2)abort();
 command=4;reads=0;if(nvme_j71s_master_guard(&p,bar)!=-EBUSY||reads)abort();
 command=0;failed=1;reads=0;if(nvme_j71s_master_guard(&p,bar)!=-EBUSY||reads)abort();
 failed=0;v=1;memcpy(bar+NVME_REG_CC,&v,4);reads=0;if(nvme_j71s_master_guard(&p,bar)!=-EBUSY||reads!=1)abort();
 v=0;memcpy(bar+NVME_REG_CC,&v,4);v=1;memcpy(bar+NVME_REG_CSTS,&v,4);reads=0;if(nvme_j71s_master_guard(&p,bar)!=-EBUSY||reads!=2)abort();
}
'''
with tempfile.TemporaryDirectory() as d:
 pth=Path(d);(pth/'t.c').write_text(p+helper+t)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(pth/'t.c'),'-o',str(pth/'t')],check=True)
 subprocess.run([str(pth/'t')],check=True)
print('J71s pre-master inherited state guard checks passed.')
