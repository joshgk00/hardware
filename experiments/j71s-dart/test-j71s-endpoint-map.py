#!/usr/bin/env python3
"""Exercise the actual software-consumer probe with a bounded DMA API mock."""
from pathlib import Path
import subprocess
import tempfile
src=(Path(__file__).parent / 'driver-patch/j71s-endpoint-map.h').read_text()
probe=src[src.index('static int j71s_endpoint_map_test'):]
prefix=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
typedef uint64_t dma_addr_t; typedef uint64_t phys_addr_t;
#define PAGE_SIZE 16384
#define GFP_KERNEL 0
#define __GFP_ZERO 0
#define DMA_BIDIRECTIONAL 0
#define DMA_BIT_MASK(n) ((1ULL<<(n))-1)
struct device {int x;}; struct pci_dev {struct device dev;};
typedef uint16_t u16;
#define __iomem
#define PCI_COMMAND 4
#define PCI_COMMAND_MASTER 4
struct iommu_domain {int type;}; struct page {int x;};
static struct iommu_domain dom={3}; static struct page page;
static int mode, frees, maps, unmaps;
static int pci_read_config_word(struct pci_dev*p,int x,u16*v){(void)p;(void)x;*v=mode==1?4:0;return 0;}
static int readl(void*p){(void)p;return 0;}
static struct iommu_domain *iommu_get_domain_for_dev(struct device *d){(void)d;return mode==2?NULL:&dom;}
static int iommu_is_dma_domain(struct iommu_domain *d){return d==&dom;}

static struct page *alloc_page(int f){(void)f;return mode==4?NULL:&page;}
static void __free_page(struct page *p){if(p!=&page)abort();frees++;}
static phys_addr_t page_to_phys(struct page *p){if(p!=&page)abort();return 0x80000000;}
static dma_addr_t dma_map_page(struct device *d,struct page *p,int o,int n,int dir){(void)d;(void)p;(void)o;(void)n;(void)dir;maps++;return mode==5?~0ULL:0x10000;}
static int dma_mapping_error(struct device *d,dma_addr_t a){(void)d;return a==~0ULL;}
static void dma_unmap_page(struct device *d,dma_addr_t a,int n,int dir){(void)d;(void)a;(void)n;(void)dir;unmaps++;}
static phys_addr_t iommu_iova_to_phys(struct iommu_domain *d,dma_addr_t a){(void)d;if(unmaps)return mode==8?1:0;if(a==0x10000)return mode==6?1:0x80000000;if(a==0x10000+PAGE_SIZE-1)return mode==7?1:0x80000000+PAGE_SIZE-1;abort();}
#define dev_info(...) ((void)0)
#define dev_err_probe(dev,err,...) (err)
'''
suffix=r'''
int main(void){struct pci_dev p={0}; char bar[64]={0};
 for(mode=0;mode<=8;mode++){frees=maps=unmaps=0;if(mode==3)continue;int ret=j71s_endpoint_map_test(&p,bar);
  if((mode==0)!=(ret==0)){fprintf(stderr,"unexpected result mode %d: %d\n",mode,ret);return 1;}
  if(mode>=5 && frees!=1){fprintf(stderr,"page leak mode %d\n",mode);return 1;}
  if((mode==0 || mode>=6) && unmaps!=1){fprintf(stderr,"missing unmap mode %d\n",mode);return 1;}
  if(mode==5 && unmaps!=0){fprintf(stderr,"invalid unmap\n");return 1;}}
 puts("Actual endpoint mapping probe: success, failures, unmap and page cleanup passed.");return 0;}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'test.c').write_text(prefix+probe+suffix)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
