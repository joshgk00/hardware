/* SPDX-License-Identifier: GPL-2.0-only */
/* One-shot experiment. Once armed, retain all buffers until physical reboot. */
#include <linux/scatterlist.h>
#include <linux/iommu.h>
extern bool j71s_test_kexec_locked(void);

static bool j71s_dma_is_identity(struct device *dev, void *cpu,
                                 dma_addr_t dma, size_t size)
{
 struct sg_table table;
 bool ok;
 int ret = dma_get_sgtable(dev, &table, cpu, dma, size);
 if (ret)
  return false;
 ok = table.nents == 1 && table.sgl->length >= size &&
      sg_phys(table.sgl) == dma;
 sg_free_table(&table);
 return ok;
}

static void j71s_test_tcb_init(struct pci_dev *pdev, void __iomem *bar,
                               struct device *host)
{
 static const u32 offsets[] = { 0x10, 0x14, 0x08, 0x0c };
 const size_t tcb_size = PAGE_ALIGN(128 * 0x80), table_size = PAGE_SIZE * 16;
 u32 saved[4], value[4], ctrl = 0;
 void *tcb = NULL, *table = NULL;
 void __iomem *mmu = NULL;
 dma_addr_t tcb_dma, table_dma;
 u64 old_mask, old_coherent;
 u16 cmd;
 unsigned int i, written = 0, errors = 0;
 bool armed = false, identity = false, retained = false;
 bool tcb_changed, table_changed;
 int ret;

 if (!j71s_test_kexec_locked() || !host->dma_mask ||
     iommu_get_domain_for_dev(host) ||
     pci_read_config_word(pdev, PCI_COMMAND, &cmd) ||
     (cmd & PCI_COMMAND_MASTER) || readl(bar + 0x14) || readl(bar + 0x1c)) {
  dev_info(host, "TCB init experiment: initial guard failed\n");
  return;
 }
 old_mask = *host->dma_mask; old_coherent = host->coherent_dma_mask;
 ret = dma_set_mask(host, DMA_BIT_MASK(36));
 if (ret)
  return;
 ret = dma_set_coherent_mask(host, DMA_BIT_MASK(36));
 if (ret) {
  dma_set_mask(host, old_mask);
  return;
 }
 tcb = dma_alloc_coherent(host, tcb_size, &tcb_dma, GFP_KERNEL | __GFP_ZERO);
 table = dma_alloc_coherent(host, table_size, &table_dma, GFP_KERNEL | __GFP_ZERO);
 if (!tcb || !table || !IS_ALIGNED(tcb_dma, SZ_4K) ||
     !IS_ALIGNED(table_dma, SZ_4K) ||
     tcb_dma > DMA_BIT_MASK(36) - (tcb_size - 1) ||
     table_dma > DMA_BIT_MASK(36) - (table_size - 1))
  goto out;
 identity = j71s_dma_is_identity(host, tcb, tcb_dma, tcb_size) &&
            j71s_dma_is_identity(host, table, table_dma, table_size);
 if (!identity)
  goto out;
 memset(tcb, 0, tcb_size);
 memset(table, 0, table_size);
 mmu = ioremap(0x601004000ULL, 0x1000);
 if (!mmu || readl(mmu + 0x04) != 0 || readl(mmu + 0x20) != 0)
  goto out;
 for (i = 0; i < ARRAY_SIZE(offsets); i++) {
  saved[i] = readl(mmu + offsets[i]);
  if (saved[i] == U32_MAX)
   goto out;
 }
 value[0] = lower_32_bits(table_dma); value[1] = upper_32_bits(table_dma);
 value[2] = lower_32_bits(tcb_dma); value[3] = upper_32_bits(tcb_dma);
 dma_wmb();
 for (i = 0; i < ARRAY_SIZE(offsets); i++) {
  if (readl(mmu + 0x04) || readl(mmu + 0x20))
   goto restore;
  writel(value[i], mmu + offsets[i]);
  written++;
  if (readl(mmu + offsets[i]) != value[i])
   goto restore;
 }
 if (!j71s_test_kexec_locked() || pci_read_config_word(pdev, PCI_COMMAND, &cmd) ||
     (cmd & PCI_COMMAND_MASTER) || readl(bar + 0x14) || readl(bar + 0x1c) ||
     readl(mmu + 0x04) || readl(mmu + 0x20))
  goto restore;
 /* Ownership is permanent before issuing the undocumented command. */
 armed = true;
 retained = true;
 dma_wmb();
 writel(0x10000, mmu + 0x04);
 ret = readl_poll_timeout(mmu + 0x04, ctrl,
                          ctrl != U32_MAX && !(ctrl & (0x10000 | 0x10)),
                          10, 250000);
 dma_rmb();
 tcb_changed = memchr_inv(tcb, 0, tcb_size) != NULL;
 table_changed = memchr_inv(table, 0, table_size) != NULL;
 dev_info(host, "TCB init experiment: armed=1 poll=%d ctrl-zero=%d bit16=%d bit4=%d all-ones=%d tcb-changed=%d table-changed=%d buffers-retained=1\n",
          ret, ctrl == 0, !!(ctrl & 0x10000), !!(ctrl & 0x10), ctrl == U32_MAX,
          tcb_changed, table_changed);
 goto out;
restore:
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
out:
 if (mmu) iounmap(mmu);
 if (!retained) {
  if (table) dma_free_coherent(host, table_size, table, table_dma);
  if (tcb) dma_free_coherent(host, tcb_size, tcb, tcb_dma);
  dma_set_mask(host, old_mask);
  dma_set_coherent_mask(host, old_coherent);
 }
 if (!armed)
  dev_info(host, "TCB init experiment: not-armed identity=%d restore-errors=%u retained=%d\n",
           identity, errors, retained);
}
