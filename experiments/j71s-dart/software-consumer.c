// SPDX-License-Identifier: GPL-2.0-only
/* J71s RAM-only software consumer for IOMMU attachment diagnostics.
 * No DMA buffers, transfers, PCIe host or physical endpoint are created.
 * Platform DMA setup happens before probe and may program DART tables/TLB.
 */
#include <linux/device.h>
#include <linux/iommu.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/platform_device.h>

static int j71s_dart_test_probe(struct platform_device *pdev)
{
	struct iommu_domain *domain;

	if (!of_machine_is_compatible("apple,j71s"))
		return -ENODEV;
	domain = iommu_get_domain_for_dev(&pdev->dev);
	if (!domain)
		return dev_err_probe(&pdev->dev, -ENODEV,
				     "no IOMMU domain attached\n");
	dev_info(&pdev->dev, "software-only DART consumer: domain type 0x%x\n",
		 domain->type);
	return 0;
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
