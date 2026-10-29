/* SPDX-License-Identifier: GPL-2.0-only */
/* Test page-table bookkeeping through the PCI endpoint, with DMA disabled. */
#include <linux/iommu.h>
#include <linux/mm.h>
static int j71s_endpoint_map_test(struct pci_dev *pdev, void __iomem *bar)
{
 struct device *dev = &pdev->dev;
 struct iommu_domain *domain;
 struct page *page;
 dma_addr_t dma;
 phys_addr_t phys, first, last, after;
 u16 command;

 if (pci_read_config_word(pdev, PCI_COMMAND, &command) ||
     (command & PCI_COMMAND_MASTER) || readl(bar + 0x14) || readl(bar + 0x1c))
  return -EINVAL;
 domain = iommu_get_domain_for_dev(dev);
 if (!domain || !iommu_is_dma_domain(domain))
  return -ENODEV;
 page = alloc_page(GFP_KERNEL | __GFP_ZERO);
 if (!page)
  return -ENOMEM;
 phys = page_to_phys(page);
 dma = dma_map_page(dev, page, 0, PAGE_SIZE, DMA_BIDIRECTIONAL);
 if (dma_mapping_error(dev, dma)) {
  __free_page(page);
  return -EIO;
 }
 first = iommu_iova_to_phys(domain, dma);
 last = iommu_iova_to_phys(domain, dma + PAGE_SIZE - 1);
 dma_unmap_page(dev, dma, PAGE_SIZE, DMA_BIDIRECTIONAL);
 after = iommu_iova_to_phys(domain, dma);
 __free_page(page);
 dev_info(dev, "experimental endpoint page map: first-match=%d last-match=%d unmapped=%d\n",
          first == phys, last == phys + PAGE_SIZE - 1, after == 0);
 return first == phys && last == phys + PAGE_SIZE - 1 && after == 0 ? 0 : -EIO;
}
