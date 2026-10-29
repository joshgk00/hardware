/* SPDX-License-Identifier: GPL-2.0-only */
/* Candidate bridge forwarding setup; no endpoint DMA is enabled here. */
static int __maybe_unused j71s_identify_root_master(void __iomem *ecam,
                        void __iomem *bar, struct j71s_identify_preparation *p,
                        struct j71s_identify_scratch *scratch, bool *attempted)
{
 u16 root, endpoint;

 if (!ecam || !bar || !p || !scratch || !attempted || *attempted ||
     !p->descriptor_published || p->armed || !scratch->retained || !scratch->ready ||
     !j71s_test_kexec_locked() || readl(ecam + 0x100000) != 0x2002106bU ||
     readl(bar + NVME_REG_CC) || readl(bar + NVME_REG_CSTS))
  return -EINVAL;
 root = readw(ecam + PCI_COMMAND);
 endpoint = readw(ecam + 0x100000 + PCI_COMMAND);
 if ((root & PCI_COMMAND_MASTER) || !(root & PCI_COMMAND_MEMORY) ||
     (root & ~(PCI_COMMAND_MEMORY | PCI_COMMAND_INTX_DISABLE)) ||
     (endpoint & PCI_COMMAND_MASTER) || !(endpoint & PCI_COMMAND_MEMORY) ||
     (endpoint & ~(PCI_COMMAND_MEMORY | PCI_COMMAND_INTX_DISABLE)))
  return -EINVAL;
 /* A failed write may have side effects; do not retry or release resources. */
 *attempted = true;
 writew(root | PCI_COMMAND_MASTER, ecam + PCI_COMMAND);
 if (readw(ecam + PCI_COMMAND) != (root | PCI_COMMAND_MASTER))
  return -EIO;
 return 0;
}
