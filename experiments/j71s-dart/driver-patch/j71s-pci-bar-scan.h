/* SPDX-License-Identifier: GPL-2.0-only */
/* Temporary PCI enumeration only; no driver binding or DMA; guarded endpoint BAR sizing. */
struct j71s_scan_state {
	void __iomem *ecam;
	struct resource buses;
	unsigned int bar_writes;
};
static void __iomem *j71s_scan_map_bus(struct pci_bus *bus, unsigned int devfn, int where)
{
	struct j71s_scan_state *state = bus->sysdata;
	if (devfn || bus->number > 1 || where < 0 || where >= 0x1000)
		return NULL;
	return state->ecam + ((unsigned long)bus->number << 20) + where;
}
static int j71s_scan_bar_write(struct pci_bus *bus, unsigned int devfn,
			      int where, int size, u32 value)
{
	struct j71s_scan_state *state = bus->sysdata;
	void __iomem *endpoint = state->ecam + 0x100000;

	if (bus->number != 1 || devfn || size != 4 ||
	    (where != PCI_BASE_ADDRESS_0 && where != PCI_BASE_ADDRESS_1) ||
	    (where == PCI_BASE_ADDRESS_0 && value != U32_MAX && value != 4) ||
	    (where == PCI_BASE_ADDRESS_1 && value != U32_MAX && value != 0) ||
	    readl(endpoint) != 0x2002106bU || (readw(endpoint + PCI_COMMAND) & 6))
		return PCIBIOS_SET_FAILED;
	state->bar_writes++;
	return pci_generic_config_write(bus, devfn, where, size, value);
}
static struct pci_ops j71s_scan_ops = {
	.map_bus = j71s_scan_map_bus,
	.read = pci_generic_config_read,
	.write = j71s_scan_bar_write,
};
static int j71s_pcie_scan_once(struct device *dev)
{
	struct pci_host_bridge *bridge;
	struct j71s_scan_state *state;
	struct pci_dev *endpoint;
	int ret;

	bridge = pci_alloc_host_bridge(sizeof(*state));
	if (!bridge)
		return -ENOMEM;
	state = pci_host_bridge_priv(bridge);
	state->ecam = devm_ioremap(dev, 0x610000000ULL, 0x200000);
	if (!state->ecam) {
		ret = -ENOMEM;
		goto out_free;
	}
	if (readl(state->ecam + 0x100000) != 0x2002106bU ||
	    readl(state->ecam + 0x100010) != 4 || readl(state->ecam + 0x100014) != 0 ||
	    (readw(state->ecam + 0x100004) & 6) || (readw(state->ecam + 4) & 6)) {
		ret = -EINVAL;
		goto out_free;
	}
	state->buses.name = "j71s temporary PCI buses";
	state->buses.start = 0;
	state->buses.end = 1;
	state->buses.flags = IORESOURCE_BUS;
	pci_add_resource(&bridge->windows, &state->buses);
	bridge->dev.parent = dev;
	bridge->sysdata = state;
	bridge->ops = &j71s_scan_ops;
	bridge->busnr = 0;
	pci_lock_rescan_remove();
	ret = pci_scan_root_bus_bridge(bridge);
	if (!ret) {
		endpoint = pci_get_domain_bus_and_slot(pci_domain_nr(bridge->bus), 1, 0);
		dev_info(dev, "experimental PCI scan: endpoint=%d expected-id=%d driver-bound=%d\n",
			 !!endpoint, endpoint && endpoint->vendor == 0x106b && endpoint->device == 0x2002,
			 endpoint && endpoint->dev.driver != NULL);
		dev_info(dev, "experimental PCI BAR scan: size=%llu memory=%d writes=%u\n",
			 endpoint ? (unsigned long long)pci_resource_len(endpoint, 0) : 0,
			 endpoint && !!(pci_resource_flags(endpoint, 0) & IORESOURCE_MEM), state->bar_writes);
		if (endpoint)
			pci_dev_put(endpoint);
		pci_stop_root_bus(bridge->bus);
		pci_remove_root_bus(bridge->bus);
	}
	pci_unlock_rescan_remove();
	dev_info(dev, "experimental PCI scan: ret=%d removed=%d bars-restored=%d\n", ret, !ret, readl(state->ecam + 0x100010) == 4 && readl(state->ecam + 0x100014) == 0);
out_free:
	pci_free_host_bridge(bridge);
	return ret;
}
