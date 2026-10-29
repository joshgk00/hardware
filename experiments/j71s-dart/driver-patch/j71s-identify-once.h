/* SPDX-License-Identifier: GPL-2.0-only */
/* Experimental one-shot Identify. No teardown: all DMA memory stays pinned. */
#include <linux/delay.h>
#include <linux/iopoll.h>
#include <linux/nvme.h>
#include <linux/pci.h>

/* Caller must have exclusively retained the TCB, SGL, SART scratch, PCI host,
 * DART domain and endpoint for the entire physical boot. This helper cannot
 * establish those ownership properties. It is deliberately not wired to probe.
 */
static int __maybe_unused j71s_identify_once(struct pci_dev *pdev, void __iomem *bar,
                      struct j71s_identify_preparation *p, u32 *tcb, u32 *sgl,
                      dma_addr_t sgl_dma, u32 scratch_iova, u32 scratch_size,
                      bool ownership_proven, u16 *nvme_status)
{
 const u32 depth = J71S_IDENTIFY_QUEUE_DEPTH;
 struct nvme_command expected;
 u64 cap, stored_sgl;
 u32 csts;
 u16 pci_command, status;
 unsigned int i;
 int ret;

 if (!ownership_proven || !j71s_test_kexec_locked() || !pdev || !bar || !p ||
     !p->sq || !p->cq || !p->payload || p->armed || !tcb || !sgl || !nvme_status ||
     !scratch_size || scratch_iova != 0xbc000000U || scratch_size != 0xe00000U ||
     pci_read_config_word(pdev, PCI_COMMAND, &pci_command) ||
     (pci_command & PCI_COMMAND_MASTER) || !(pci_command & PCI_COMMAND_MEMORY) ||
     readl(bar + NVME_REG_CC) || readl(bar + NVME_REG_CSTS))
  return -EINVAL;
 cap = (u64)readl(bar + NVME_REG_CAP) | ((u64)readl(bar + NVME_REG_CAP + 4) << 32);
 if (cap == U64_MAX || NVME_CAP_MQES(cap) + 1 < depth ||
     NVME_CAP_MPSMIN(cap) > 0 || !(NVME_CAP_CSS(cap) & NVME_CAP_CSS_NVM) ||
     readl(bar + 0x1810) != scratch_iova || readl(bar + 0x1814) ||
     readl(bar + 0x1818) != scratch_size ||
     !j71s_identify_window_contains(p->sq_dma, PAGE_SIZE) ||
     !j71s_identify_window_contains(p->cq_dma, PAGE_SIZE))
  return -EINVAL;
 j71s_identify_build_command(&expected);
 memcpy(&stored_sgl, &tcb[4], sizeof(stored_sgl));
 if (memchr_inv(p->cq, 0, PAGE_SIZE) ||
     memcmp(&p->sq[0], &expected, sizeof(expected)) ||
     READ_ONCE(tcb[0]) != 0x200 || READ_ONCE(tcb[1]) != 1 ||
     READ_ONCE(tcb[2]) != (p->payload_phys >> 12) ||
     READ_ONCE(sgl[0]) != (p->payload_phys >> 12) || stored_sgl != sgl_dma)
  return -EINVAL;

 /* From here on even failed writes require holding every resource until reset. */
 p->armed = true;
 dma_wmb();
 writel(U32_MAX, bar + NVME_REG_INTMS);
 writel((depth - 1) | ((depth - 1) << 16), bar + NVME_REG_AQA);
 writel(lower_32_bits(p->sq_dma), bar + NVME_REG_ASQ);
 writel(upper_32_bits(p->sq_dma), bar + NVME_REG_ASQ + 4);
 writel(lower_32_bits(p->cq_dma), bar + NVME_REG_ACQ);
 writel(upper_32_bits(p->cq_dma), bar + NVME_REG_ACQ + 4);
 pci_set_master(pdev);
 if (pci_read_config_word(pdev, PCI_COMMAND, &pci_command) ||
     !(pci_command & PCI_COMMAND_MASTER))
  return -EIO;
 writel(NVME_CC_ENABLE | NVME_CC_IOSQES | NVME_CC_IOCQES, bar + NVME_REG_CC);
 ret = readl_poll_timeout(bar + NVME_REG_CSTS, csts,
                          csts == U32_MAX || (csts & (NVME_CSTS_RDY | NVME_CSTS_CFS)),
                          1000, 5000000);
 if (ret || csts == U32_MAX || (csts & NVME_CSTS_CFS) || !(csts & NVME_CSTS_RDY))
  return ret ? ret : -EIO;
 dma_wmb();
 writel(1, bar + NVME_REG_DBS);
 for (i = 0; i < 5000; i++) {
  status = le16_to_cpu(READ_ONCE(p->cq[0].status));
  if (status & 1) {
   dma_rmb();
   if (p->cq[0].command_id != cpu_to_le16(1) ||
       le16_to_cpu(p->cq[0].sq_id) != 0)
    return -EIO;
   *nvme_status = status >> 1;
   return 0;
  }
  usleep_range(1000, 2000);
 }
 return -ETIMEDOUT;
}
