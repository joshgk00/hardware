/* SPDX-License-Identifier: GPL-2.0-only */
#include <linux/scatterlist.h>
#include <linux/iommu.h>
static bool j71s_dma_is_identity(struct device *dev, void *cpu,
                                 dma_addr_t dma, size_t size)
{
 struct sg_table table;
 bool ok;
 int ret = dma_get_sgtable(dev, &table, cpu, dma, size);
 if (ret)
  return false;
 ok = table.nents == 1 && table.sgl->length >= size &&
      sg_phys(table.sgl) == dma;
 sg_free_table(&table);
 return ok;
}

static void j71s_test_tcb_preflight(struct pci_dev *pdev, void __iomem *bar,
                                    struct device *host)
{
 const size_t ts = PAGE_ALIGN(128 * 0x80), ss = PAGE_SIZE * 16;
 void *tcb = NULL, *table = NULL;
 dma_addr_t td, sd;
 u64 old, oldc;
 u16 cmd;
 bool ok = false;
 int ret, restore;

 if (!host->dma_mask || iommu_get_domain_for_dev(host) ||
     pci_read_config_word(pdev, PCI_COMMAND, &cmd) ||
     (cmd & PCI_COMMAND_MASTER) || readl(bar + 0x14) || readl(bar + 0x1c)) {
  dev_info(host, "TCB preflight: guard failed\n");
  return;
 }
 old = *host->dma_mask; oldc = host->coherent_dma_mask;
 ret = dma_set_mask(host, DMA_BIT_MASK(36));
 if (ret) return;
 ret = dma_set_coherent_mask(host, DMA_BIT_MASK(36));
 if (ret) { dma_set_mask(host, old); return; }
 tcb = dma_alloc_coherent(host, ts, &td, GFP_KERNEL | __GFP_ZERO);
 table = dma_alloc_coherent(host, ss, &sd, GFP_KERNEL | __GFP_ZERO);
 if (tcb && table && IS_ALIGNED(td, SZ_4K) && IS_ALIGNED(sd, SZ_4K) &&
     td <= DMA_BIT_MASK(36) - (ts - 1) && sd <= DMA_BIT_MASK(36) - (ss - 1))
  ok = j71s_dma_is_identity(host, tcb, td, ts) &&
       j71s_dma_is_identity(host, table, sd, ss);
 if (table) dma_free_coherent(host, ss, table, sd);
 if (tcb) dma_free_coherent(host, ts, tcb, td);
 restore = dma_set_mask(host, old);
 restore |= dma_set_coherent_mask(host, oldc);
 dev_info(host, "TCB preflight: identity=%d buffers=%d masks-restored=%d\n",
          ok, !!tcb && !!table, !restore);
}
