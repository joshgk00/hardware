/* SPDX-License-Identifier: GPL-2.0-only */
struct j71s_scan_state {
	void __iomem *ecam;
	struct resource buses;
	struct resource mem;
	unsigned int bar_writes;
 bool msi_active;
 u16 msi_ctrl, msi_data;
 u32 msi_lo, msi_hi;
};
static int j71s_scan_bar_write(struct pci_bus *bus, unsigned int devfn,
			      int where, int size, u32 value)
{
	struct j71s_scan_state *state = bus->sysdata;
	void __iomem *endpoint = state->ecam + 0x100000;

	if (bus->number == 1 && !devfn && state->msi_active &&
	    readl(endpoint) == 0x2002106bU &&
	    !(readw(endpoint + PCI_COMMAND) & PCI_COMMAND_MASTER)) {
		if (where == PCI_COMMAND && size == 2 &&
		    !(value & ~(PCI_COMMAND_MEMORY | PCI_COMMAND_INTX_DISABLE)))
			return pci_generic_config_write(bus, devfn, where, size, value);
		if (where == 0x52 && size == 2 &&
		    (value & ~(PCI_MSI_FLAGS_ENABLE | PCI_MSI_FLAGS_QSIZE)) ==
		    (state->msi_ctrl & ~(PCI_MSI_FLAGS_ENABLE | PCI_MSI_FLAGS_QSIZE)))
			return pci_generic_config_write(bus, devfn, where, size, value);
		if (where == 0x54 && size == 4 &&
		    (value == lower_32_bits(J71S_TEST_MSI_DOORBELL) || value == state->msi_lo))
			return pci_generic_config_write(bus, devfn, where, size, value);
		if (where == 0x58 && size == 4 &&
		    (value == upper_32_bits(J71S_TEST_MSI_DOORBELL) || value == state->msi_hi))
			return pci_generic_config_write(bus, devfn, where, size, value);
		if (where == 0x5c && size == 2 && (value == 0 || value == state->msi_data))
			return pci_generic_config_write(bus, devfn, where, size, value);
	}
	if (bus->number == 1 && !devfn && where == PCI_COMMAND && size == 2 &&
	    !(value & ~PCI_COMMAND_MEMORY) && readl(endpoint) == 0x2002106bU &&
	    !(readw(endpoint + PCI_COMMAND) & PCI_COMMAND_MASTER))
		return pci_generic_config_write(bus, devfn, where, size, value);

	if (bus->number != 1 || devfn || size != 4 ||
	    (where != PCI_BASE_ADDRESS_0 && where != PCI_BASE_ADDRESS_1) ||
	    (where == PCI_BASE_ADDRESS_0 && value != U32_MAX && value != 4 && value != 0xc0000004U) ||
	    (where == PCI_BASE_ADDRESS_1 && value != U32_MAX && value != 0) ||
	    readl(endpoint) != 0x2002106bU || (readw(endpoint + PCI_COMMAND) & 6))
		return PCIBIOS_SET_FAILED;
	state->bar_writes++;
	return pci_generic_config_write(bus, devfn, where, size, value);
}
