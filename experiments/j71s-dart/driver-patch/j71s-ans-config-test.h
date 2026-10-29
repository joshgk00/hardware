/* SPDX-License-Identifier: GPL-2.0-only */
/* Candidate S8000 ANS PCI config; controller off, restore each saved value. */
static void j71s_test_ans_config(struct pci_dev *pdev, void __iomem *bar)
{
 struct j71s_scan_state *state = pdev->bus->sysdata;
 static const u32 offsets[] = { 0x17c, 0x18c, 0x188 };
 const u32 desired[] = { 0x10081008, 0, 0x40440000 };
 u32 saved[3], observed;
 u16 cmd;
 unsigned int i, written = 0, errors = 0, failed_at = 3;
 int status = 0;
 bool matched = true, safe = true, write_failed = false, read_failed = false;

 if (pci_find_ext_capability(pdev, PCI_EXT_CAP_ID_LTR) != 0x178 ||
     pci_find_ext_capability(pdev, PCI_EXT_CAP_ID_L1SS) != 0x180 ||
     pci_read_config_word(pdev, PCI_COMMAND, &cmd) ||
     (cmd & PCI_COMMAND_MASTER) || readl(bar + 0x14) || readl(bar + 0x1c))
  return;
 for (i = 0; i < ARRAY_SIZE(offsets); i++)
  if (pci_read_config_dword(pdev, offsets[i], &saved[i]) || saved[i] == U32_MAX)
   return;
 state->ans_ltr = saved[0]; state->ans_ctl2 = saved[1]; state->ans_ctl1 = saved[2];
 state->ans_cfg_active = true;
 for (i = 0; i < ARRAY_SIZE(offsets); i++) {
  if (pci_read_config_word(pdev, PCI_COMMAND, &cmd) ||
      (cmd & PCI_COMMAND_MASTER) || readl(bar + 0x14) || readl(bar + 0x1c)) {
   matched = false; safe = false; failed_at = i; break;
  }
  /* A failed write can still have side effects; attempt to restore it. */
  written = i + 1;
  status = pci_write_config_dword(pdev, offsets[i], desired[i]);
  if (status) { matched = false; write_failed = true; failed_at = i; break; }
  status = pci_read_config_dword(pdev, offsets[i], &observed);
  if (status || observed != desired[i]) { matched = false; read_failed = !!status; failed_at = i; break; }
 }
 while (written && safe) {
  if (pci_read_config_word(pdev, PCI_COMMAND, &cmd) ||
      (cmd & PCI_COMMAND_MASTER) || readl(bar + 0x14) || readl(bar + 0x1c)) {
   safe = false; break;
  }
  i = --written;
  status = pci_write_config_dword(pdev, offsets[i], saved[i]);
  if (status) errors++;
  status = pci_read_config_dword(pdev, offsets[i], &observed);
  if (status || observed != saved[i]) errors++;
 }
 state->ans_cfg_active = false;
 dev_info(&pdev->dev, "experimental ANS config: matched=%d restore-errors=%u remaining=%u safe=%d failed-index=%u write-failed=%d read-failed=%d\n",
          matched, errors, written, safe, failed_at, write_failed, read_failed);
}
