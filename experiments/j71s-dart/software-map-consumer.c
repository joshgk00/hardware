// SPDX-License-Identifier: GPL-2.0-only
/* J71s RAM-only software consumer for IOMMU attachment diagnostics.
 * Maps one RAM page in software; no physical DMA, PCIe host or endpoint.
 * Platform DMA setup happens before probe and may program DART tables/TLB.
 */
#include <linux/device.h>
#include <linux/dma-mapping.h>
#include <linux/mm.h>
#include <linux/iommu.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/platform_device.h>

static int j71s_dart_test_probe(struct platform_device *pdev)
{
	struct iommu_domain *domain;
	struct page *page;
	dma_addr_t dma;
	phys_addr_t phys, first, last, after;
	int ret;

	if (!of_machine_is_compatible("apple,j71s"))
		return -ENODEV;
	domain = iommu_get_domain_for_dev(&pdev->dev);
	if (!domain || !iommu_is_dma_domain(domain))
		return dev_err_probe(&pdev->dev, -ENODEV,
				     "no DMA IOMMU domain attached\n");
	dev_info(&pdev->dev, "software-only DART consumer: domain type 0x%x\n",
		 domain->type);
	ret = dma_set_mask_and_coherent(&pdev->dev, DMA_BIT_MASK(32));
	if (ret)
		return dev_err_probe(&pdev->dev, ret, "software mapping DMA mask\n");
	page = alloc_page(GFP_KERNEL | __GFP_ZERO);
	if (!page)
		return -ENOMEM;
	phys = page_to_phys(page);
	dma = dma_map_page(&pdev->dev, page, 0, PAGE_SIZE, DMA_BIDIRECTIONAL);
	if (dma_mapping_error(&pdev->dev, dma)) {
		__free_page(page);
		return dev_err_probe(&pdev->dev, -EIO, "software page map failed\n");
	}
	first = iommu_iova_to_phys(domain, dma);
	last = iommu_iova_to_phys(domain, dma + PAGE_SIZE - 1);
	dma_unmap_page(&pdev->dev, dma, PAGE_SIZE, DMA_BIDIRECTIONAL);
	after = iommu_iova_to_phys(domain, dma);
	__free_page(page);
	dev_info(&pdev->dev, "software-only mapping: first_match=%d last_match=%d unmapped=%d\n",
		 first == phys, last == phys + PAGE_SIZE - 1, after == 0);
	return first == phys && last == phys + PAGE_SIZE - 1 && after == 0 ? 0 : -EIO;
}

static const struct of_device_id j71s_dart_test_of_match[] = {
	{ .compatible = "orchard,j71s-dart-test" },
	{}
};
MODULE_DEVICE_TABLE(of, j71s_dart_test_of_match);

static struct platform_driver j71s_dart_test_driver = {
	.probe = j71s_dart_test_probe,
	.driver = {
		.name = "j71s-dart-software-test",
		.of_match_table = j71s_dart_test_of_match,
	},
};
module_platform_driver(j71s_dart_test_driver);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Experimental J71s DART software-only consumer");
