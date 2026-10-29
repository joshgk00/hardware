/* SPDX-License-Identifier: GPL-2.0-only */
/* One MSI allocation with controller and PCI bus mastering disabled. */
static void j71s_test_msi_allocation(struct pci_dev *pdev, void __iomem *bar)
{
 struct j71s_scan_state *state = pdev->bus->sysdata;
 u16 cmd, control, data, current_ctrl = 0, current_data = 0, current_cmd = 0;
 u32 lo, hi, current_lo = 0, current_hi = 0;
 int ret, restore = 0, matching = 0, disabled = 0;

 if (pdev->msi_cap != 0x50 || !dev_get_msi_domain(&pdev->dev) ||
     pci_read_config_word(pdev, PCI_COMMAND, &cmd) ||
     (cmd & (PCI_COMMAND_MASTER | PCI_COMMAND_INTX_DISABLE)) ||
     readl(bar + 0x14) || readl(bar + 0x1c) ||
     pci_read_config_word(pdev, 0x52, &control) ||
     !(control & PCI_MSI_FLAGS_64BIT) || (control & PCI_MSI_FLAGS_ENABLE) ||
     pci_read_config_dword(pdev, 0x54, &lo) ||
     pci_read_config_dword(pdev, 0x58, &hi) ||
     pci_read_config_word(pdev, 0x5c, &data)) {
  dev_info(&pdev->dev, "experimental MSI allocation: guard failed\n");
  return;
 }
 state->msi_ctrl = control; state->msi_data = data;
 state->msi_lo = lo; state->msi_hi = hi;
 state->msi_active = true;
 ret = pci_alloc_irq_vectors(pdev, 1, 1, PCI_IRQ_MSI);
 if (ret == 1) {
  pci_read_config_word(pdev, 0x52, &current_ctrl);
  pci_read_config_dword(pdev, 0x54, &current_lo);
  pci_read_config_dword(pdev, 0x58, &current_hi);
  pci_read_config_word(pdev, 0x5c, &current_data);
  pci_read_config_word(pdev, PCI_COMMAND, &current_cmd);
  matching = (current_ctrl & PCI_MSI_FLAGS_ENABLE) &&
    current_lo == lower_32_bits(J71S_TEST_MSI_DOORBELL) &&
    current_hi == upper_32_bits(J71S_TEST_MSI_DOORBELL) &&
    current_data == 0 && !(current_cmd & PCI_COMMAND_MASTER);
  pci_free_irq_vectors(pdev);
 }
 pci_read_config_word(pdev, 0x52, &current_ctrl);
 disabled = !(current_ctrl & PCI_MSI_FLAGS_ENABLE);
 if (disabled) {
  restore |= pci_write_config_dword(pdev, 0x54, lo);
  restore |= pci_write_config_dword(pdev, 0x58, hi);
  restore |= pci_write_config_word(pdev, 0x5c, data);
  restore |= pci_write_config_word(pdev, 0x52, control);
  restore |= pci_write_config_word(pdev, PCI_COMMAND, cmd);
  restore |= pci_read_config_dword(pdev, 0x54, &current_lo);
  restore |= pci_read_config_dword(pdev, 0x58, &current_hi);
  restore |= pci_read_config_word(pdev, 0x5c, &current_data);
  restore |= pci_read_config_word(pdev, 0x52, &current_ctrl);
  restore |= pci_read_config_word(pdev, PCI_COMMAND, &current_cmd);
  if (current_lo != lo || current_hi != hi || current_data != data ||
      current_ctrl != control || current_cmd != cmd)
   restore = -EIO;
 } else {
  restore = -EIO;
 }
 state->msi_active = false;
 dev_info(&pdev->dev, "experimental MSI allocation: ret=%d matching=%d disabled=%d restored=%d\n",
          ret, matching, disabled, !restore);
}
