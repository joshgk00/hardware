#!/usr/bin/env python3
"""Exercise the actual candidate probe sequence with simulated helper failures."""
from pathlib import Path
import subprocess,tempfile
lines=(Path(__file__).parent/'j71s-identify-coordinator-candidate.patch').read_text().splitlines()
start=next(i for i,x in enumerate(lines) if x.startswith('+\t\t\tif (!descriptor_ret &&'))
end=next(i for i,x in enumerate(lines[start:],start) if x.startswith(' \t\t\tif (!data->descriptor.published)'))
block='\n'.join(x[1:] for x in lines[start:end] if x.startswith('+'))
gate_patch=(Path(__file__).parent/'j71s-identify-observer-gate.patch').read_text()
assert '+\t\t\tif (!descriptor_ret && READ_ONCE(j71s_identify_start) &&' in gate_patch
block=block.replace('if (!descriptor_ret && of_property_read_bool',
                    'if (!descriptor_ret && READ_ONCE(j71s_identify_start) && of_property_read_bool',1)
preamble=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
typedef uint16_t u16;typedef uint64_t dma_addr_t;
#define U16_MAX UINT16_MAX
#define J71S_SCRATCH_IOVA 0xbc000000U
#define J71S_SCRATCH_BYTES 0xe00000U
#define dev_info(...) ((void)0)
#define READ_ONCE(x) (x)
struct j71s_identify_preparation {int value;};
struct j71s_identify_descriptor {int *tcb,*sgl;dma_addr_t sgl_dma;};
struct j71s_identify_scratch {int value;};
struct data {void *bar;struct j71s_identify_preparation prepared;struct j71s_identify_descriptor descriptor;struct j71s_identify_scratch scratch;bool root_master_attempted;};
struct j71s_scan_state {void *ecam;struct j71s_identify_preparation *identify_owner;struct j71s_identify_scratch *identify_scratch;bool identify_opted_in;};
struct device {void *of_node;};struct bridge {struct {struct device *parent;} dev;};struct bus {void *sysdata;};struct pci_dev {struct bus *bus;struct device dev;};
static int property,scratch_ret,root_ret,once_ret,steps,root_calls,once_calls;static bool j71s_identify_start;
static bool of_property_read_bool(void *node,const char *name){(void)node;(void)name;return property;}
static int j71s_identify_setup_scratch(struct pci_dev *d,void *b,struct j71s_identify_scratch *s){(void)d;(void)b;(void)s;steps=steps*10+1;return scratch_ret;}
static int j71s_identify_root_master(void *e,void *b,struct j71s_identify_preparation *p,struct j71s_identify_scratch *s,bool *a){(void)e;(void)b;(void)p;(void)s;(void)a;steps=steps*10+2;root_calls++;return root_ret;}
static int j71s_identify_once(struct pci_dev *dev,void *bar,struct j71s_identify_preparation *p,int *t,int *s,dma_addr_t d,unsigned int i,unsigned int z,bool owner,u16 *status){(void)bar;(void)t;(void)s;(void)d;(void)i;(void)z;struct j71s_scan_state *st=dev->bus->sysdata;if(!owner||!st->identify_opted_in||st->identify_owner!=p||!st->identify_scratch)abort();steps=steps*10+3;once_calls++;*status=0;return once_ret;}
static void run(struct pci_dev *pdev,struct bridge *host,struct data *data,int descriptor_ret){
'''
test=r'''
}
int main(void){struct j71s_scan_state state={0};struct bus bus={.sysdata=&state};struct pci_dev pdev={.bus=&bus};struct device parent={0};struct bridge host={.dev={.parent=&parent}};struct data data={0};
 property=0;run(&pdev,&host,&data,0);if(steps||root_calls||once_calls)abort();
 property=1;run(&pdev,&host,&data,0);if(steps||root_calls||once_calls)abort();
 j71s_identify_start=true;run(&pdev,&host,&data,-1);if(steps||root_calls||once_calls)abort();
 scratch_ret=-1;run(&pdev,&host,&data,0);if(steps!=1||root_calls||once_calls||state.identify_opted_in)abort();
 scratch_ret=0;root_ret=-1;steps=0;run(&pdev,&host,&data,0);if(steps!=12||root_calls!=1||once_calls||state.identify_opted_in)abort();
 root_ret=0;steps=0;run(&pdev,&host,&data,0);if(steps!=123||root_calls!=2||once_calls!=1||state.identify_opted_in)abort();
 once_ret=-1;steps=0;run(&pdev,&host,&data,0);if(steps!=123||state.identify_opted_in)abort();
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'test.c').write_text(preamble+block+test)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('Identify coordinator opt-in, ordering and helper failures passed.')
