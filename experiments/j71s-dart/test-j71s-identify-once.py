#!/usr/bin/env python3
"""Exercise the actual one-shot function with a fake NVMe controller."""
from pathlib import Path
import subprocess, tempfile
src=(Path(__file__).parent/'driver-patch/j71s-identify-once.h').read_text()
fn=src[src.index('static int __maybe_unused'):]
preamble=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
typedef uint64_t u64; typedef uint32_t u32; typedef uint16_t u16; typedef uint64_t dma_addr_t;
#define __maybe_unused
#define __iomem
#define PAGE_SIZE 4096
#define BIT(n) (1U<<(n))
#define U32_MAX UINT32_MAX
#define U64_MAX UINT64_MAX
#define J71S_IDENTIFY_QUEUE_DEPTH 16
#define J71S_IDENTIFY_FLATDMA 0x40000000ULL
#define NVME_IDENTIFY_DATA_SIZE 4096
#define NVME_REG_CAP 0
#define NVME_REG_INTMS 0xc
#define NVME_REG_CC 0x14
#define NVME_REG_CSTS 0x1c
#define NVME_REG_AQA 0x24
#define NVME_REG_ASQ 0x28
#define NVME_REG_ACQ 0x30
#define NVME_REG_DBS 0x1000
#define NVME_CC_ENABLE 1
#define NVME_CC_IOSQES (6<<16)
#define NVME_CC_IOCQES (4<<20)
#define NVME_CSTS_RDY 1
#define NVME_CSTS_CFS 2
#define NVME_CAP_MQES(x) ((x)&0xffff)
#define NVME_CAP_MPSMIN(x) (((x)>>48)&15)
#define NVME_CAP_CSS(x) (((x)>>37)&255)
#define NVME_CAP_CSS_NVM 1
#define PCI_COMMAND_MASTER 4
#define PCI_COMMAND_MEMORY 2
#define PCI_COMMAND 4
#define READ_ONCE(x) (x)
#define cpu_to_le16(x) (x)
#define cpu_to_le64(x) (x)
#define le16_to_cpu(x) (x)
#define lower_32_bits(x) ((u32)(x))
#define upper_32_bits(x) ((u32)((u64)(x)>>32))
#define pr_info(...) ((void)0)
#define dma_wmb() ((void)0)
#define dma_rmb() ((void)0)
#define usleep_range(a,b) ((void)0)
#define msleep(a) do { if ((a)!=100) abort(); sleeps++; } while (0)
#define readl_poll_timeout(addr,val,cond,delay,timeout) ((val)=readl(addr), (cond)?0:-ETIMEDOUT)
struct nvme_command { struct { uint8_t opcode,flags; u16 command_id; u32 nsid; u64 reserved[2]; struct {u64 prp1,prp2;} dptr; uint8_t cns,rest[23]; } identify; };
struct nvme_completion { u64 result; u16 sq_head,sq_id,command_id,status; };
struct j71s_identify_preparation {struct nvme_command *sq; struct nvme_completion *cq; void *payload; u64 sq_dma,cq_dma,payload_dma,payload_phys; bool armed,descriptor_published;};
struct pci_dev {u16 command,vendor; bool reject_master;};
static struct j71s_identify_preparation *active; static unsigned char registers[0x2000],port_regs[0x1000]; static int writes; static int complete,payload_mode,sleeps,link_reads,link_fail_at,port_unmaps,endpoint_reads,cfg_reads,reads_at_enable;
static bool j71s_test_kexec_locked(void) {return true;}
static bool j71s_identify_window_contains(u64 n,size_t size) {return n>=0x80000000 && n<0xbc000000 && size<=0xbc000000-n;}
static void j71s_identify_build_command(struct nvme_command *p) {memset(p,0,sizeof(*p));p->identify.opcode=6;p->identify.flags=32;p->identify.command_id=1;p->identify.dptr.prp1=0x40000000;p->identify.cns=1;}
static void *memchr_inv(const void *ptr,int value,size_t n) {const unsigned char *p=ptr;while(n--){if(*p!=(unsigned char)value)return (void*)p;p++;}return NULL;}
static void *ioremap(u64 addr,size_t size) {if(addr!=0x601000000ULL||size!=0x1000)abort();return port_regs;}
static void iounmap(void *p) {if(p!=port_regs)abort();port_unmaps++;}
static u32 readl(const void *p) {u32 v;if(p==port_regs+0x88){link_reads++;return link_fail_at && link_reads>=link_fail_at ? 0:1;}endpoint_reads++;memcpy(&v,p,4);return v;}
static void writel(u32 v,void *p) {size_t off=(unsigned char*)p-registers;writes++;memcpy(p,&v,4);if(off==NVME_REG_CC&&v&1){u32 ready=1;reads_at_enable=endpoint_reads;memcpy(registers+NVME_REG_CSTS,&ready,4);}if(off==NVME_REG_DBS&&!sleeps)abort();if(off==NVME_REG_DBS&&complete){active->cq->status=1;active->cq->command_id=1;if(payload_mode){((unsigned char *)active->payload)[0]=payload_mode==1?0x6b:0x12;((unsigned char *)active->payload)[1]=0x10;}}}
static int pci_read_config_word(struct pci_dev *p,int where,u16 *v) {(void)where;cfg_reads++;*v=p->command;return 0;}
static void pci_set_master(struct pci_dev *p) {if(!p->reject_master)p->command|=PCI_COMMAND_MASTER;}
'''
checks=r'''
int main(void) {
 struct pci_dev d={.command=PCI_COMMAND_MEMORY,.vendor=0x106b}; struct nvme_command sq[64]={0}; struct nvme_completion cq[256]={0}; unsigned char payload[4096]={0};
 struct j71s_identify_preparation p={.sq=sq,.cq=cq,.payload=payload,.sq_dma=0x80000000,.cq_dma=0x80001000,.payload_phys=0x100000,.descriptor_published=true};
 u32 tcb[32]={0},sgl[256]={0}; u64 sgl_dma=0x200000; u16 status=999; u32 cap_lo=0x10003ff,cap_hi=0x20,scratch=0xbc000000,size=0xe00000;
 memcpy(registers,&cap_lo,4);memcpy(registers+4,&cap_hi,4);memcpy(registers+0x1810,&scratch,4);memcpy(registers+0x1818,&size,4);
 tcb[0]=0x200;tcb[1]=1;tcb[2]=0x100;sgl[0]=0x100;memcpy(&tcb[4],&sgl_dma,8);j71s_identify_build_command(sq);active=&p;
 if(j71s_identify_once(&d,registers,&p,tcb,sgl,sgl_dma,scratch,size,false,false,&status)!=-EINVAL || writes || p.armed)abort();
 sq[0].identify.rest[2]=9;
 if(j71s_identify_once(&d,registers,&p,tcb,sgl,sgl_dma,scratch,size,true,false,&status)!=-EINVAL || writes || p.armed)abort();
 j71s_identify_build_command(sq);port_unmaps=0;link_reads=0;endpoint_reads=0;cfg_reads=0;link_fail_at=1;
 if(j71s_identify_once(&d,registers,&p,tcb,sgl,sgl_dma,scratch,size,true,false,&status)!=-ENOLINK || p.armed || writes || port_unmaps!=1 || endpoint_reads || cfg_reads)abort();
 link_fail_at=2;link_reads=0;
 if(j71s_identify_once(&d,registers,&p,tcb,sgl,sgl_dma,scratch,size,true,false,&status)!=-ENOLINK || !p.armed || writes!=7 || port_unmaps!=2 || endpoint_reads!=reads_at_enable)abort();
 memset(registers+0x14,0,4);memset(registers+0x1c,0,4);p.armed=false;d.command=PCI_COMMAND_MEMORY;writes=0;link_fail_at=0;link_reads=0;d.reject_master=true;
 if(j71s_identify_once(&d,registers,&p,tcb,sgl,sgl_dma,scratch,size,true,false,&status)!=-EIO || !p.armed || writes!=6)abort();
 memset(registers+0x14,0,4);memset(registers+0x1c,0,4);p.armed=false;d.reject_master=false;d.command=PCI_COMMAND_MEMORY;writes=0;link_fail_at=103;link_reads=0;sleeps=0;
 if(j71s_identify_once(&d,registers,&p,tcb,sgl,sgl_dma,scratch,size,true,false,&status)!=-ENOLINK || !p.armed || writes!=7 || sleeps!=101)abort();
 memset(registers+0x14,0,4);memset(registers+0x1c,0,4);p.armed=false;d.command=PCI_COMMAND_MEMORY;writes=0;link_fail_at=0;link_reads=0;sleeps=0;complete=1;payload_mode=1;
 if(j71s_identify_once(&d,registers,&p,tcb,sgl,sgl_dma,scratch,size,true,false,&status) || !p.armed || status!=0 || !(d.command&PCI_COMMAND_MASTER) || sleeps!=102)abort();
 if(j71s_identify_once(&d,registers,&p,tcb,sgl,sgl_dma,scratch,size,true,false,&status)!=-EINVAL)abort();
 memset(registers+0x14,0,4);memset(registers+0x1c,0,4);memset(cq,0,sizeof(cq));memset(payload,0,sizeof(payload));
 p.armed=false;d.command=PCI_COMMAND_MEMORY;complete=0;
 if(j71s_identify_once(&d,registers,&p,tcb,sgl,sgl_dma,scratch,size,true,false,&status)!=-ETIMEDOUT || !p.armed)abort();
 memset(registers+0x14,0,4);memset(registers+0x1c,0,4);memset(cq,0,sizeof(cq));memset(payload,0,sizeof(payload));
 p.armed=false;d.command=PCI_COMMAND_MEMORY;complete=1;payload_mode=0;
 if(j71s_identify_once(&d,registers,&p,tcb,sgl,sgl_dma,scratch,size,true,false,&status)!=-EBADMSG || !p.armed)abort();
 memset(registers+0x14,0,4);memset(registers+0x1c,0,4);memset(cq,0,sizeof(cq));memset(payload,0,sizeof(payload));
 p.armed=false;d.command=PCI_COMMAND_MEMORY;payload_mode=2;
 if(j71s_identify_once(&d,registers,&p,tcb,sgl,sgl_dma,scratch,size,true,false,&status)!=-EBADMSG || !p.armed)abort();
 memset(registers+0x14,0,4);memset(registers+0x1c,0,4);memset(cq,0,sizeof(cq));memset(payload,0,sizeof(payload));
 p.armed=false;d.command=PCI_COMMAND_MEMORY;writes=0;sleeps=0;status=999;complete=1;payload_mode=1;
 if(j71s_identify_once(&d,registers,&p,tcb,sgl,sgl_dma,scratch,size,true,true,&status) || !p.armed || writes!=7 || sleeps!=100 || status!=999 || cq[0].status)abort();
 memset(registers+0x14,0,4);memset(registers+0x1c,0,4);memset(cq,0,sizeof(cq));memset(payload,0,sizeof(payload));
 p.armed=false;d.command=PCI_COMMAND_MEMORY;writes=0;sleeps=0;link_reads=0;link_fail_at=3;
 if(j71s_identify_once(&d,registers,&p,tcb,sgl,sgl_dma,scratch,size,true,true,&status)!=-ENOLINK || !p.armed || writes!=7 || sleeps)abort();
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'test.c').write_text(preamble+fn+checks)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('One-shot link guards, retention, completion and response validation passed.')
