/* SPDX-License-Identifier: GPL-2.0-only */
/* Candidate HMB/SART setup for a one-shot test; never tears down after writes. */
#include <linux/ioport.h>
#include <linux/of_reserved_mem.h>

#define J71S_SCRATCH_IOVA 0xbc000000U
#define J71S_SCRATCH_BYTES 0xe00000U

struct j71s_identify_scratch {
 void *cpu;
 void __iomem *mmu;
 bool retained;
 bool ready;
};

/* Caller must retain the PCI endpoint, diagnostic host and all DMA domains
 * until physical reset. A nonzero return after retained=1 is not a rollback.
 * Do not use this candidate to justify releasing any hardware-owned memory.
 */
static int __maybe_unused j71s_identify_setup_scratch(struct pci_dev *pdev,
                       void __iomem *bar, struct j71s_identify_scratch *s)
{
 struct device_node *node;
 struct reserved_mem *r;
 const u32 offsets[] = { 0x24, 0x28, 0x2c };
 u32 values[3];
 u16 command;
 unsigned int i;
 int ret = -EINVAL;

 if (!pdev || !bar || !s || s->retained || !j71s_test_kexec_locked() ||
     pci_read_config_word(pdev, PCI_COMMAND, &command) ||
     (command & PCI_COMMAND_MASTER) || readl(bar + NVME_REG_CC) ||
     readl(bar + NVME_REG_CSTS))
  return -EINVAL;
 node = of_find_node_by_path("/reserved-memory/j71s-nvme-scratch");
 r = node ? of_reserved_mem_lookup(node) : NULL;
 if (!r || !of_property_read_bool(node, "no-map") ||
     of_property_read_bool(node, "reusable") || r->size != J71S_SCRATCH_BYTES ||
     !IS_ALIGNED(r->base, SZ_1M) || (r->base >> 20) > U32_MAX ||
     r->base > DMA_BIT_MASK(36) - (r->size - 1) ||
     region_intersects(r->base, r->size, IORESOURCE_SYSTEM_RAM, IORES_DESC_NONE) != REGION_DISJOINT)
  goto out_node;
 s->cpu = memremap(r->base, r->size, MEMREMAP_WB);
 if (!s->cpu) {
  ret = -ENOMEM;
  goto out_node;
 }
 s->mmu = ioremap(0x601004000ULL, 0x1000);
 if (!s->mmu) {
  ret = -ENOMEM;
  goto unmap;
 }
 if (readl(s->mmu + 0x20) || readl(s->mmu + 0x04) ||
     readl(bar + 0x1810) || readl(bar + 0x1814) || readl(bar + 0x1818) ||
     readl(s->mmu + 0x24) == U32_MAX || readl(s->mmu + 0x28) == U32_MAX ||
     !(readl(s->mmu + 0x24) & BIT(31)) || !(readl(s->mmu + 0x28) & BIT(31)))
  goto unmap;
 values[0] = J71S_SCRATCH_IOVA - 0x80000000U;
 values[1] = J71S_SCRATCH_IOVA + J71S_SCRATCH_BYTES - 0x80100000U;
 values[2] = r->base >> 20;
 memset(s->cpu, 0, r->size);
 wmb();
 if (!j71s_test_kexec_locked() || pci_read_config_word(pdev, PCI_COMMAND, &command) ||
     (command & PCI_COMMAND_MASTER) || readl(bar + NVME_REG_CC) ||
     readl(bar + NVME_REG_CSTS) || readl(s->mmu + 0x20) || readl(s->mmu + 0x04))
  goto unmap;
 /* Window writes can expose the reservation; retain it on every later path. */
 s->retained = true;
 for (i = 0; i < ARRAY_SIZE(offsets); i++) {
  writel(values[i], s->mmu + offsets[i]);
  if (readl(s->mmu + offsets[i]) != (values[i] | (i < 2 ? BIT(31) : 0))) {
   ret = -EIO;
   goto out_node;
  }
 }
 writel(1, s->mmu + 0x20);
 if (readl(s->mmu + 0x20) != 1) {
  ret = -EIO;
  goto out_node;
 }
 writel(J71S_SCRATCH_IOVA, bar + 0x1810);
 writel(0, bar + 0x1814);
 writel(J71S_SCRATCH_BYTES, bar + 0x1818);
 if (readl(bar + 0x1810) != J71S_SCRATCH_IOVA || readl(bar + 0x1814) ||
     readl(bar + 0x1818) != J71S_SCRATCH_BYTES) {
  ret = -EIO;
  goto out_node;
 }
 s->ready = true;
 ret = 0;
 goto out_node;
unmap:
 if (s->mmu) { iounmap(s->mmu); s->mmu = NULL; }
 if (s->cpu) { memunmap(s->cpu); s->cpu = NULL; }
out_node:
 of_node_put(node);
 return ret;
}
