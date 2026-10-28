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

/* Test candidate window fields with its control disabled and no PCI DMA. */
static void j71s_test_nvmmu_window(struct pci_dev *pdev, void __iomem *bar)
{
	const u32 offsets[3] = { 0x24, 0x28, 0x2c };
	const u32 candidate_iova = 0xbc000000U;
	struct device *dev = &pdev->dev;
	struct device_node *node;
	struct reserved_mem *region;
	void __iomem *mmu = NULL;
	u32 saved[3], desired[3];
	u16 command;
	unsigned int i, written = 0, errors = 0;
	bool matched = true, disabled = false, enabled = false;

	node = of_find_node_by_path("/reserved-memory/j71s-nvme-scratch");
	region = node ? of_reserved_mem_lookup(node) : NULL;
	if (!region || !of_property_read_bool(node, "no-map") ||
	    of_property_read_bool(node, "reusable") || region->size != 0xe00000 ||
	    !IS_ALIGNED(region->base, 0x100000) || (region->base >> 20) > U32_MAX ||
	    region_intersects(region->base, region->size, IORESOURCE_SYSTEM_RAM, IORES_DESC_NONE) != REGION_DISJOINT ||
	    pci_read_config_word(pdev, PCI_COMMAND, &command) || (command & PCI_COMMAND_MASTER) ||
	    readl(bar + 0x14) != 0 || readl(bar + 0x1c) != 0)
		goto out;
	mmu = ioremap(0x601004000ULL, 0x1000);
	if (!mmu || readl(mmu + 0x20) != 0 || readl(mmu + 0x04) != 0)
		goto out;
	for (i = 0; i < 3; i++) {
		saved[i] = readl(mmu + offsets[i]);
		if (saved[i] == U32_MAX)
			goto out;
	}
	if (!(saved[0] & BIT(31)) || !(saved[1] & BIT(31)))
		goto out;
	desired[0] = candidate_iova - 0x80000000U;
	desired[1] = candidate_iova + (u32)region->size - 0x80100000U;
	desired[2] = region->base >> 20;
	for (i = 0; i < 3; i++) {
		if (readl(mmu + 0x20) != 0) {
			matched = false;
			break;
		}
		writel(desired[i], mmu + offsets[i]);
		written++;
		{
			u32 observed = readl(mmu + offsets[i]);

			if (observed != (desired[i] | (i < 2 ? BIT(31) : 0))) {
				dev_info(dev, "experimental NVMMU mismatch: index=%u observed-zero=%d unchanged=%d all-ones=%d\n",
					 i, !observed, observed == saved[i], observed == U32_MAX);
				matched = false;
				break;
			}
			dev_info(dev, "experimental NVMMU field: index=%u matched=1\n", i);
		}
	}
	if (matched && written == 3 && readl(mmu + 0x20) == 0 &&
	    !pci_read_config_word(pdev, PCI_COMMAND, &command) &&
	    !(command & PCI_COMMAND_MASTER) && readl(bar + 0x14) == 0 && readl(bar + 0x1c) == 0) {
		writel(1, mmu + 0x20);
		enabled = readl(mmu + 0x20) == 1;
		writel(0, mmu + 0x20);
	}
	disabled = readl(mmu + 0x20) == 0;
	dev_info(dev, "experimental NVMMU control: enabled-readback=%d disabled-readback=%d\n", enabled, disabled);
	if (disabled) {
		while (written) {
			i = --written;
			writel(saved[i], mmu + offsets[i]);
			if (readl(mmu + offsets[i]) != saved[i])
				errors++;
		}
	}
	dev_info(dev, "experimental NVMMU window: matched=%d control-off=%d restore-errors=%u remaining=%u\n",
		 matched, disabled, errors, written);
out:
	if (mmu)
		iounmap(mmu);
	of_node_put(node);
}
