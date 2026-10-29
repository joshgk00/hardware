from pathlib import Path
import subprocess,tempfile
s=(Path(__file__).parent / 'driver-patch/j71s-msi-alloc-test.h').read_text();s=s[s.index('static void j71s_test_msi_allocation'):]
p=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <errno.h>
typedef uint16_t u16;typedef uint32_t u32;
#define __iomem
#define PCI_COMMAND 4
#define PCI_COMMAND_MASTER 4
#define PCI_COMMAND_INTX_DISABLE 0x400
#define PCI_MSI_FLAGS_64BIT 0x80
#define PCI_MSI_FLAGS_ENABLE 1
#define PCI_IRQ_MSI 1
#define J71S_TEST_MSI_DOORBELL 0xbffff000ULL
#define lower_32_bits(x) ((u32)(x))
#define upper_32_bits(x) ((u32)((x)>>32))
struct j71s_scan_state{bool msi_active;u16 msi_ctrl,msi_data;u32 msi_lo,msi_hi;};
struct bus{void*sysdata;};struct device{int x;};struct pci_dev{struct bus*bus;struct device dev;int msi_cap;};
static unsigned char cfg[256];static int mode,allocs,frees,write_count,report_ret,report_match,report_disabled,report_restored;
static void *dev_get_msi_domain(struct device*d){(void)d;return mode==1?NULL:(void*)1;}
static int pci_read_config_word(struct pci_dev*d,int o,u16*v){(void)d;memcpy(v,cfg+o,2);return 0;}
static int pci_read_config_dword(struct pci_dev*d,int o,u32*v){(void)d;memcpy(v,cfg+o,4);return 0;}
static int pci_write_config_word(struct pci_dev*d,int o,u16 v){(void)d;write_count++;memcpy(cfg+o,&v,2);return 0;}
static int pci_write_config_dword(struct pci_dev*d,int o,u32 v){(void)d;write_count++;memcpy(cfg+o,&v,4);return 0;}
static u32 readl(void*p){u32 v;memcpy(&v,p,4);return v;}
static int pci_alloc_irq_vectors(struct pci_dev*d,int a,int b,int c){(void)d;(void)a;(void)b;(void)c;allocs++;if(mode==2)return -ENOSPC;u16 ctrl=0x81;u32 lo=0xbffff000,hi=0;u16 data=0;memcpy(cfg+0x52,&ctrl,2);memcpy(cfg+0x54,&lo,4);memcpy(cfg+0x58,&hi,4);memcpy(cfg+0x5c,&data,2);return 1;}
static void pci_free_irq_vectors(struct pci_dev*d){(void)d;frees++;if(mode!=3)cfg[0x52]&=~1;}
static void dev_info(struct device*d,const char*fmt,...){(void)d;if(strstr(fmt,"ret=%d")){__builtin_va_list a;__builtin_va_start(a,fmt);report_ret=__builtin_va_arg(a,int);report_match=__builtin_va_arg(a,int);report_disabled=__builtin_va_arg(a,int);report_restored=__builtin_va_arg(a,int);__builtin_va_end(a);}}
'''
t=r'''
int main(void){struct j71s_scan_state st={0};struct bus bus={&st};struct pci_dev p={&bus,{0},0x50};unsigned char bar[64]={0};
 for(mode=0;mode<=3;mode++){memset(cfg,0,sizeof(cfg));cfg[0x52]=0x80;cfg[4]=2;allocs=frees=write_count=0;report_ret=report_match=report_disabled=report_restored=0;j71s_test_msi_allocation(&p,bar);
  if(st.msi_active)abort();
  if(mode==0 && (allocs!=1||frees!=1||!report_match||!report_disabled||!report_restored))abort();
  if(mode==1 && (allocs||write_count))abort();
  if(mode==2 && (allocs!=1||frees||!report_disabled||!report_restored))abort();
  if(mode==3 && (frees!=1||report_disabled||report_restored||write_count))abort();
 }
}
'''
with tempfile.TemporaryDirectory() as d:
 pth=Path(d);(pth/'t.c').write_text(p+s+t)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(pth/'t.c'),'-o',str(pth/'t')],check=True)
 subprocess.run([str(pth/'t')],check=True)
print('MSI allocation, missing-domain, allocation failure and unsafe-disable guards passed.')
