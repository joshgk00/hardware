/* SPDX-License-Identifier: GPL-2.0-only */
/* Candidate NVMMU table-address readback only; never start the NVMMU. */
static void j71s_test_tcb_addresses(struct pci_dev *pdev, void __iomem *bar,
                                   struct device *host)
{
 static const u32 offsets[] = { 0x10, 0x14, 0x08, 0x0c };
 const size_t tcb_size = PAGE_ALIGN(128 * 0x80), table_size = PAGE_SIZE * 16;
 u32 saved[4], value[4];
 void *tcb = NULL, *table = NULL;
 void __iomem *mmu = NULL;
 dma_addr_t tcb_dma, table_dma;
 u64 old_mask, old_coherent;
 u16 cmd;
 unsigned int i, written = 0, errors = 0, nonzero = 0;
 bool matched = true, retained = false, masks_set = false;
 int ret;

 if (!host->dma_mask || pci_read_config_word(pdev, PCI_COMMAND, &cmd) ||
     (cmd & PCI_COMMAND_MASTER) || readl(bar + 0x14) || readl(bar + 0x1c))
  return;
 old_mask = *host->dma_mask; old_coherent = host->coherent_dma_mask;
 ret = dma_set_mask(host, DMA_BIT_MASK(64));
 if (ret)
  return;
 ret = dma_set_coherent_mask(host, DMA_BIT_MASK(64));
 if (ret) {
  dma_set_mask(host, old_mask);
  return;
 }
 masks_set = true;
 tcb = dma_alloc_coherent(host, tcb_size, &tcb_dma, GFP_KERNEL | __GFP_ZERO);
 table = dma_alloc_coherent(host, table_size, &table_dma, GFP_KERNEL | __GFP_ZERO);
 if (!tcb || !table || !IS_ALIGNED(tcb_dma, SZ_4K) || !IS_ALIGNED(table_dma, SZ_4K))
  goto out;
 mmu = ioremap(0x601004000ULL, 0x1000);
 if (!mmu || readl(mmu + 0x04) != 0 || readl(mmu + 0x20) != 0)
  goto out;
 for (i = 0; i < ARRAY_SIZE(offsets); i++) {
  saved[i] = readl(mmu + offsets[i]);
  if (saved[i] == U32_MAX)
   goto out;
  nonzero += saved[i] != 0;
 }
 value[0] = lower_32_bits(table_dma); value[1] = upper_32_bits(table_dma);
 value[2] = lower_32_bits(tcb_dma); value[3] = upper_32_bits(tcb_dma);
 dma_wmb();
 for (i = 0; i < ARRAY_SIZE(offsets); i++) {
  if (readl(mmu + 0x04) != 0 || readl(mmu + 0x20) != 0) {
   matched = false;
   break;
  }
  writel(value[i], mmu + offsets[i]);
  written++;
  if (readl(mmu + offsets[i]) != value[i]) {
   matched = false;
   break;
  }
 }
 if (readl(mmu + 0x04) || readl(mmu + 0x20)) {
  retained = true;
 } else {
  while (written) {
   if (readl(mmu + 0x04) || readl(mmu + 0x20)) {
    retained = true;
    break;
   }
   i = --written;
   writel(saved[i], mmu + offsets[i]);
   if (readl(mmu + offsets[i]) != saved[i])
    errors++;
  }
  retained |= errors != 0 || written != 0;
 }
 dev_info(host, "experimental TCB addresses: matched=%d restore-errors=%u retained=%d baseline-nonzero=%u\n",
          matched, errors, retained, nonzero);
out:
 if (mmu)
  iounmap(mmu);
 if (!retained) {
  if (table) dma_free_coherent(host, table_size, table, table_dma);
  if (tcb) dma_free_coherent(host, tcb_size, tcb, tcb_dma);
  if (masks_set) {
   ret = dma_set_mask(host, old_mask);
   ret |= dma_set_coherent_mask(host, old_coherent);
   dev_info(host, "experimental TCB buffers: masks-restored=%d\n", !ret);
  }
 }
}
