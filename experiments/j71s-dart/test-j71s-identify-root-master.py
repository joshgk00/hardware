#!/usr/bin/env python3
"""Check root-master guards and one-shot failure handling with fake MMIO."""
from pathlib import Path
import subprocess,tempfile
src=(Path(__file__).parent/'driver-patch/j71s-identify-root-master.h').read_text()
fn=src[src.index('static int'):]
preamble=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
typedef uint16_t u16;typedef uint32_t u32;
#define __iomem
#define __maybe_unused
#define PCI_COMMAND 4
#define PCI_COMMAND_MEMORY 2
#define PCI_COMMAND_MASTER 4
#define PCI_COMMAND_INTX_DISABLE 1024
#define NVME_REG_CC 0x14
#define NVME_REG_CSTS 0x1c
struct j71s_identify_preparation {bool descriptor_published,armed;};
struct j71s_identify_scratch {bool retained,ready;};
static int writes;static bool wrong_write,locked=true;
static bool j71s_test_kexec_locked(void){return locked;}
static u16 readw(const void *p){u16 x;memcpy(&x,p,2);return x;}
static u32 readl(const void *p){u32 x;memcpy(&x,p,4);return x;}
static void writew(u16 x,void *p){writes++;if(wrong_write)x^=1;memcpy(p,&x,2);}
'''
test=r'''
int main(void){
 unsigned char *ecam=calloc(1,0x101000),bar[8192]={0};u32 id=0x2002106b;u16 mem=2;bool attempted=false;
 struct j71s_identify_preparation p={.descriptor_published=1};struct j71s_identify_scratch s={.retained=1,.ready=1};
 memcpy(ecam+0x100000,&id,4);memcpy(ecam+4,&mem,2);memcpy(ecam+0x100004,&mem,2);
 s.ready=0;if(j71s_identify_root_master(ecam,bar,&p,&s,&attempted)!=-EINVAL||writes||attempted)abort();s.ready=1;
 locked=0;if(j71s_identify_root_master(ecam,bar,&p,&s,&attempted)!=-EINVAL||writes||attempted)abort();locked=1;
 wrong_write=1;if(j71s_identify_root_master(ecam,bar,&p,&s,&attempted)!=-EIO||writes!=1||!attempted)abort();
 if(j71s_identify_root_master(ecam,bar,&p,&s,&attempted)!=-EINVAL||writes!=1)abort();
 memcpy(ecam+4,&mem,2);attempted=false;wrong_write=false;writes=0;
 if(j71s_identify_root_master(ecam,bar,&p,&s,&attempted)||!attempted||writes!=1||readw(ecam+4)!=6||readw(ecam+0x100004)!=2)abort();
 free(ecam);
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'test.c').write_text(preamble+fn+test)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('Bridge one-shot guard and failed-write handling passed.')
