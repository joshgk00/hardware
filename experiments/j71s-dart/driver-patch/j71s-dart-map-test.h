/* SPDX-License-Identifier: GPL-2.0-only */
/* Temporary manual DART lifecycle test; no hardware DMA is enabled. */
static void j71s_pcie_dart_coexist_test(struct device *parent)
{
 struct device_node *np;
 struct platform_device *existing, *dart;
 int ret;
 bool applied = false;
 struct of_changeset cs;
 u32 map[4], mask = 0xff00;

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
 of_changeset_init(&cs);
 if (!dart->dev.driver || !np->phandle ||
     of_find_property(parent->of_node, "iommu-map", NULL) ||
     of_find_property(parent->of_node, "iommu-map-mask", NULL)) {
  dev_err(parent, "coexist DART map: guard failed\n");
  goto out_dart;
 }
 /* Tentative J71b mapping; no bus mastering or physical DMA is allowed. */
 map[0] = 0x100; map[1] = np->phandle; map[2] = 0; map[3] = 1;
 ret = of_changeset_update_prop_string(&cs, np, "status", "okay");
 if (!ret)
  ret = of_changeset_add_prop_u32_array(&cs, parent->of_node, "iommu-map", map, 4);
 if (!ret)
  ret = of_changeset_add_prop_u32_array(&cs, parent->of_node, "iommu-map-mask", &mask, 1);
 if (!ret)
  ret = of_changeset_apply(&cs);
 if (ret) {
  dev_err(parent, "coexist DART map: changeset failed=%d\n", ret);
  goto out_dart;
 }
 applied = true;
 dev_info(parent, "coexist DART map: applied requester 0x100 stream 0\n");
 j71s_pcie_scan_once(parent);
out_dart:
 platform_device_unregister(dart);
 of_node_clear_flag(np, OF_POPULATED);
 dev_info(parent, "coexist DART: unregistered before host cleanup\n");
 if (applied) {
  ret = of_changeset_revert(&cs);
  dev_info(parent, "coexist DART map: revert=%d\n", ret);
 }
 of_changeset_destroy(&cs);
out_flag:
 of_node_clear_flag(np, OF_POPULATED);
out_node:
 of_node_put(np);
}
