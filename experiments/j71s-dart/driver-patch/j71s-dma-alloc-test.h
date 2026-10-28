/* SPDX-License-Identifier: GPL-2.0-only */
/* Allocate and free candidate queue/translation buffers; no hardware DMA. */
#include <linux/dma-mapping.h>
#include <linux/sizes.h>

static void j71s_test_dma_allocations(struct pci_dev *pdev, void __iomem *bar)
{
	struct device *dev = &pdev->dev;
	const size_t sizes[5] = {
		PAGE_ALIGN(36 * 0x80), PAGE_SIZE * 16,
		PAGE_ALIGN(36 * 256 * sizeof(u32)), PAGE_SIZE, PAGE_SIZE,
	};
	void *cpu[5] = { NULL };
	dma_addr_t dma[5];
	u64 old_dma_mask, old_coherent_mask;
	u16 command;
	unsigned int i, allocated = 0;
	bool aligned = true, pattern_ok = true;
	int ret, mask_restore, coherent_restore;

	if (!dev->dma_mask || pci_read_config_word(pdev, PCI_COMMAND, &command) ||
	    (command & PCI_COMMAND_MASTER) || readl(bar + 0x14) != 0 || readl(bar + 0x1c) != 0) {
		dev_info(dev, "experimental DMA allocation: guard failed\n");
		return;
	}
	old_dma_mask = *dev->dma_mask;
	old_coherent_mask = dev->coherent_dma_mask;
	ret = dma_set_mask(dev, DMA_BIT_MASK(64));
	if (!ret) {
		ret = dma_set_coherent_mask(dev, DMA_BIT_MASK(64));
		if (ret)
			dma_set_mask(dev, old_dma_mask);
	}
	if (ret) {
		dev_info(dev, "experimental DMA allocation: mask failed=%d\n", ret);
		return;
	}
	for (i = 0; i < ARRAY_SIZE(sizes); i++) {
		cpu[i] = dma_alloc_coherent(dev, sizes[i], &dma[i], GFP_KERNEL);
		if (!cpu[i])
			break;
		allocated++;
		aligned &= IS_ALIGNED(dma[i], SZ_4K);
		WRITE_ONCE(*(u32 *)cpu[i], 0x5a3cc3a5U);
		WRITE_ONCE(*(u32 *)(cpu[i] + sizes[i] - sizeof(u32)), 0xa5c33c5aU);
		dma_wmb();
		pattern_ok &= READ_ONCE(*(u32 *)cpu[i]) == 0x5a3cc3a5U &&
			      READ_ONCE(*(u32 *)(cpu[i] + sizes[i] - sizeof(u32))) == 0xa5c33c5aU;
	}
	for (i = allocated; i > 0; i--) {
		unsigned int n = i - 1;

		memset(cpu[n], 0, sizes[n]);
		dma_free_coherent(dev, sizes[n], cpu[n], dma[n]);
	}
	mask_restore = dma_set_mask(dev, old_dma_mask);
	coherent_restore = dma_set_coherent_mask(dev, old_coherent_mask);
	dev_info(dev, "experimental DMA allocation: allocated=%u aligned=%d cpu-patterns=%d masks-restored=%d\n",
		 allocated, aligned, pattern_ok, !mask_restore && !coherent_restore);
}
