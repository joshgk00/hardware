from pathlib import Path
import subprocess,tempfile
s=(Path(__file__).parent / 'driver-patch/j71s-ans-config-test.h').read_text();s=s[s.index('static void j71s_test_ans_config'):]
p=r'''
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
typedef uint8_t u8;typedef uint16_t u16;typedef uint32_t u32;
#define __iomem
#define U32_MAX UINT32_MAX
#define PCI_COMMAND 4
#define PCI_COMMAND_MASTER 4
#define PCI_EXT_CAP_ID_LTR 0x18
#define PCI_EXT_CAP_ID_L1SS 0x1e
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
struct j71s_scan_state {bool ans_cfg_active;u8 ans_latency;u32 ans_ltr,ans_ctl1,ans_ctl2;};
struct bus {void*sysdata;};struct device{int x;};struct pci_dev{struct bus*bus;struct device dev;};
static unsigned char cfg[512];static int fail_at,writes,report_matched,report_errors,report_remaining,report_safe,master;
static int pci_find_ext_capability(struct pci_dev*p,int id){(void)p;return id==PCI_EXT_CAP_ID_LTR?0x178:0x180;}
static int pci_read_config_word(struct pci_dev*p,int o,u16*v){(void)p;(void)o;*v=master?4:0;return 0;}
static int pci_read_config_dword(struct pci_dev*p,int o,u32*v){(void)p;memcpy(v,cfg+o,4);return 0;}
static int pci_write_config_dword(struct pci_dev*p,int o,u32 v){(void)p;memcpy(cfg+o,&v,4);writes++;return writes==fail_at?-1:0;}
static u32 readl(void*p){u32 v;memcpy(&v,p,4);return v;}
static void dev_info(struct device*d,const char*fmt,...){(void)d;(void)fmt;va_list a;va_start(a,fmt);report_matched=va_arg(a,int);report_errors=va_arg(a,unsigned);report_remaining=va_arg(a,unsigned);report_safe=va_arg(a,int);va_end(a);}
'''
t=r'''
int main(void){struct j71s_scan_state st={0};struct bus bus={&st};struct pci_dev p={&bus,{0}};unsigned char bar[64]={0};unsigned char original[512];
 for(fail_at=0;fail_at<=3;fail_at++){for(int i=0;i<512;i++)cfg[i]=(unsigned char)i;memcpy(original,cfg,512);writes=report_matched=report_errors=report_remaining=report_safe=0;j71s_test_ans_config(&p,bar);
  if(memcmp(cfg,original,512)||st.ans_cfg_active||report_errors||report_remaining||!report_safe)abort();
  if(!fail_at&&(writes!=6||!report_matched))abort();
  if(fail_at&&(writes!=2*fail_at||report_matched))abort();
 }
 master=1;writes=0;j71s_test_ans_config(&p,bar);if(writes)abort();
}
'''
with tempfile.TemporaryDirectory() as d:
 pth=Path(d);(pth/'t.c').write_text(p+s+t)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(pth/'t.c'),'-o',str(pth/'t')],check=True)
 subprocess.run([str(pth/'t')],check=True)
print('ANS config writes, side-effecting failures and reverse restoration passed.')
