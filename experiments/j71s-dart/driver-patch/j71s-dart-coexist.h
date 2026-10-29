/* SPDX-License-Identifier: GPL-2.0-only */
/* Temporary manual DART lifecycle test; no hardware DMA is enabled. */
static void j71s_pcie_dart_coexist_test(struct device *parent)
{
 struct device_node *np;
 struct platform_device *existing, *dart;
 int ret;

 np = of_find_node_by_path("/soc/iommu@601008000");
 if (!np || of_device_is_available(np) ||
     !of_device_is_compatible(np, "apple,s5l8960x-dart")) {
  dev_err(parent, "coexist DART: unexpected node state\n");
  goto out_node;
 }
 existing = of_find_device_by_node(np);
 if (existing) {
  put_device(&existing->dev);
  dev_err(parent, "coexist DART: device already exists\n");
  goto out_node;
 }
 if (of_node_test_and_set_flag(np, OF_POPULATED)) {
  dev_err(parent, "coexist DART: node already populated\n");
  goto out_node;
 }
 dart = of_device_alloc(np, NULL, parent);
 if (!dart) {
  dev_err(parent, "coexist DART: allocation failed\n");
  goto out_flag;
 }
 dart->dev.coherent_dma_mask = DMA_BIT_MASK(32);
 dart->dev.dma_mask = &dart->dev.coherent_dma_mask;
 dart->dev.bus = &platform_bus_type;
 ret = of_device_add(dart);
 if (ret) {
  dev_err(parent, "coexist DART: add failed=%d\n", ret);
  platform_device_put(dart);
  goto out_flag;
 }
 dev_info(parent, "coexist DART: registered driver-bound=%d\n", !!dart->dev.driver);
 if (dart->dev.driver)
  j71s_pcie_scan_once(parent);
 else
  dev_err(parent, "coexist DART: driver did not bind; skipping scan\n");
 platform_device_unregister(dart);
 dev_info(parent, "coexist DART: unregistered before host cleanup\n");
out_flag:
 of_node_clear_flag(np, OF_POPULATED);
out_node:
 of_node_put(np);
}
