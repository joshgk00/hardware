from pathlib import Path
import subprocess,tempfile
source=(Path(__file__).parent / 'driver-patch/j71s-dart-coexist.h').read_text()
preamble=r'''
#include <stdlib.h>
#include <stdbool.h>
#include <stdint.h>
struct device_node {int available, compatible, populated;};
struct device {void *driver; uint64_t coherent_dma_mask,*dma_mask; void *bus;};
struct platform_device {struct device dev;};
static struct device_node node; static struct platform_device dart;
static int exists,alloc_fail,add_fail,bound,scans,removed,puts,nodeputs;
static int platform_bus_type;
#define OF_POPULATED 1
#define DMA_BIT_MASK(x) UINT32_MAX
#define dev_err(...) ((void)0)
#define dev_info(...) ((void)0)
static struct device_node *of_find_node_by_path(const char *p){(void)p;return &node;}
static int of_device_is_available(struct device_node*n){return n->available;}
static int of_device_is_compatible(struct device_node*n,const char*s){(void)s;return n->compatible;}
static struct platform_device *of_find_device_by_node(struct device_node*n){(void)n;return exists?&dart:NULL;}
static void put_device(struct device*d){(void)d;puts++;}
static int of_node_test_and_set_flag(struct device_node*n,int f){(void)f;if(n->populated)return 1;n->populated=1;return 0;}
static void of_node_clear_flag(struct device_node*n,int f){(void)f;n->populated=0;}
static void of_node_put(struct device_node*n){(void)n;nodeputs++;}
static struct platform_device *of_device_alloc(struct device_node*n,const char*s,struct device*d){(void)n;(void)s;(void)d;return alloc_fail?NULL:&dart;}
static int of_device_add(struct platform_device*p){p->dev.driver=bound?(void*)1:NULL;return add_fail?-1:0;}
static void platform_device_put(struct platform_device*p){(void)p;puts++;}
static void platform_device_unregister(struct platform_device*p){(void)p;removed++;}
static void j71s_pcie_scan_once(struct device*d){(void)d;scans++;}
'''
test=r'''
static void reset(void){node=(struct device_node){0,1,0};dart=(struct platform_device){0};exists=alloc_fail=add_fail=bound=scans=removed=puts=nodeputs=0;}
int main(void){struct device parent={0};
 reset();bound=1;j71s_pcie_dart_coexist_test(&parent);if(scans!=1||removed!=1||node.populated||nodeputs!=1)abort();
 reset();j71s_pcie_dart_coexist_test(&parent);if(scans||removed!=1||node.populated)abort();
 reset();add_fail=1;j71s_pcie_dart_coexist_test(&parent);if(scans||removed||puts!=1||node.populated)abort();
 reset();alloc_fail=1;j71s_pcie_dart_coexist_test(&parent);if(scans||removed||node.populated)abort();
 reset();exists=1;j71s_pcie_dart_coexist_test(&parent);if(scans||puts!=1||node.populated)abort();
 reset();node.available=1;j71s_pcie_dart_coexist_test(&parent);if(scans||removed||node.populated)abort();
 reset();node.populated=1;j71s_pcie_dart_coexist_test(&parent);if(scans||removed||!node.populated)abort();
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'t.c').write_text(preamble+source+test)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(p/'t.c'),'-o',str(p/'t')],check=True)
 subprocess.run([str(p/'t')],check=True)
print('DART coexistence lifecycle and failure guards passed (mock).')
