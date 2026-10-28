/* SPDX-License-Identifier: GPL-2.0-only */
/* Isolated scratch CPU mapping and NVMMU register observations; no DMA. */
#include <linux/of_reserved_mem.h>

static void j71s_test_reserved_scratch(struct device *dev)
{
	struct device_node *node;
	struct reserved_mem *region;
	void *mapping;
	u64 *words[3], saved[3];
	const u64 patterns[3] = { 0x123456789abcdef0ULL, 0xfedcba9876543210ULL, 0x55aa55aa33cc33ccULL };
	bool passed = true, restored = true;
	int i;

	node = of_find_node_by_path("/reserved-memory/j71s-nvme-scratch");
	region = node ? of_reserved_mem_lookup(node) : NULL;
	if (!region || !of_property_read_bool(node, "no-map") ||
	    of_property_read_bool(node, "reusable") || region->size != 0xe00000 ||
	    !IS_ALIGNED(region->base, 0x100000) ||
	    region_intersects(region->base, region->size, IORESOURCE_SYSTEM_RAM, IORES_DESC_NONE) != REGION_DISJOINT) {
		dev_info(dev, "experimental scratch RAM: reservation guard failed\n");
		goto out_node;
	}
	mapping = memremap(region->base, region->size, MEMREMAP_WB);
	if (!mapping) {
		dev_info(dev, "experimental scratch RAM: map failed\n");
		goto out_node;
	}
	words[0] = mapping;
	words[1] = mapping + region->size / 2;
	words[2] = mapping + region->size - sizeof(u64);
	for (i = 0; i < 3; i++)
		saved[i] = READ_ONCE(*words[i]);
	for (i = 0; i < 3; i++)
		WRITE_ONCE(*words[i], patterns[i]);
	mb();
	for (i = 0; i < 3; i++)
		passed &= READ_ONCE(*words[i]) == patterns[i];
	for (i = 0; i < 3; i++)
		WRITE_ONCE(*words[i], saved[i]);
	mb();
	for (i = 0; i < 3; i++)
		restored &= READ_ONCE(*words[i]) == saved[i];
	memunmap(mapping);
	dev_info(dev, "experimental scratch RAM: mapped=1 patterns-match=%d restored=%d\n", passed, restored);
out_node:
	of_node_put(node);
}

static void j71s_observe_nvmmu(struct device *dev)
{
	void __iomem *mmu = ioremap(0x601004000ULL, 0x1000);
	u32 ctrl, start, end, physical;

	if (!mmu) {
		dev_info(dev, "experimental NVMMU fields: map failed\n");
		return;
	}
	ctrl = readl(mmu + 0x20);
	start = readl(mmu + 0x24);
	end = readl(mmu + 0x28);
	physical = readl(mmu + 0x2c);
	dev_info(dev, "experimental NVMMU fields: ctrl-zero=%d start-zero=%d end-zero=%d physical-zero=%d any-all-ones=%d\n",
		 !ctrl, !start, !end, !physical,
		 ctrl == U32_MAX || start == U32_MAX || end == U32_MAX || physical == U32_MAX);
	iounmap(mmu);
}
