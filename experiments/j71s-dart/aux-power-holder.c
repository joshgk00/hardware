// SPDX-License-Identifier: GPL-2.0
/* Isolated J71s diagnostic: keep the single DT power domain attached. */
#include <linux/module.h>
#include <linux/of.h>
#include <linux/platform_device.h>

static int j71s_aux_hold_probe(struct platform_device *pdev)
{
	if (!of_machine_is_compatible("apple,j71s"))
		return -ENODEV;
	dev_info(&pdev->dev, "experimental PCIe AUX power-domain holder bound\n");
	return 0;
}

static const struct of_device_id j71s_aux_hold_match[] = {
	{ .compatible = "orchard,j71s-pcie-aux-test" },
	{ }
};
MODULE_DEVICE_TABLE(of, j71s_aux_hold_match);
static struct platform_driver j71s_aux_hold_driver = {
	.probe = j71s_aux_hold_probe,
	.driver = {
		.name = "j71s-pcie-aux-test",
		.of_match_table = j71s_aux_hold_match,
	},
};
module_platform_driver(j71s_aux_hold_driver);
MODULE_LICENSE("GPL");
