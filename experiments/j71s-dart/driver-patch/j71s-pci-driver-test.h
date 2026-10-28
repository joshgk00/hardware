/* SPDX-License-Identifier: GPL-2.0-only */
/* Temporary PCI enumeration only; no driver binding or DMA; guarded endpoint BAR sizing. */
struct j71s_scan_state {
	void __iomem *ecam;
	struct resource buses;
	struct resource mem;
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
static struct pci_ops j71s_scan_ops = {
	.map_bus = j71s_scan_map_bus,
	.read = pci_generic_config_read,
	.write = j71s_scan_bar_write,
};
static int j71s_pcie_test_iomap(struct device *dev,
		struct j71s_scan_state *state, struct pci_dev *endpoint)
{
	void __iomem *bar;
	u16 root_cmd = readw(state->ecam + PCI_COMMAND);
	u16 ep_cmd = readw(state->ecam + 0x100000 + PCI_COMMAND);
	int ret = -EIO;

	if ((root_cmd & 6) || (ep_cmd & 6) ||
	    readl(state->ecam + 0x100010) != 0xc0000004U ||
	    readl(state->ecam + 0x100014) != 0)
		return -EINVAL;
	bar = pci_iomap(endpoint, 0, 0);
	if (!bar)
		return -ENOMEM;
	writew(root_cmd | PCI_COMMAND_MEMORY, state->ecam + PCI_COMMAND);
	if (readw(state->ecam + PCI_COMMAND) != (root_cmd | PCI_COMMAND_MEMORY))
		goto restore_root;
	writew(ep_cmd | PCI_COMMAND_MEMORY, state->ecam + 0x100000 + PCI_COMMAND);
	if (readw(state->ecam + 0x100000 + PCI_COMMAND) == (ep_cmd | PCI_COMMAND_MEMORY)) {
		u32 version = readl(bar + 8);

		dev_info(dev, "experimental PCI iomap: version=%#x master-off=%d\n",
			 version, !(readw(state->ecam + 0x100000 + PCI_COMMAND) & PCI_COMMAND_MASTER));
		ret = version == 0x10001 ? 0 : -EIO;
	}
	writew(ep_cmd, state->ecam + 0x100000 + PCI_COMMAND);
	dev_info(dev, "experimental PCI iomap: endpoint command restored=%d\n",
		 readw(state->ecam + 0x100000 + PCI_COMMAND) == ep_cmd);
restore_root:
	writew(root_cmd, state->ecam + PCI_COMMAND);
	dev_info(dev, "experimental PCI iomap: root command restored=%d\n",
		 readw(state->ecam + PCI_COMMAND) == root_cmd);
	pci_iounmap(endpoint, bar);
	return ret;
}

struct j71s_pci_test_data {
	void __iomem *bar;
	u16 saved_command;
};

static void j71s_pci_test_remove(struct pci_dev *pdev)
{
	struct j71s_pci_test_data *data = pci_get_drvdata(pdev);
	u16 command;
	int status;

	if (!data)
		return;
	pci_set_drvdata(pdev, NULL);
	pci_iounmap(pdev, data->bar);
	pci_disable_device(pdev);
	status = pci_write_config_word(pdev, PCI_COMMAND, data->saved_command);
	status |= pci_read_config_word(pdev, PCI_COMMAND, &command);
	dev_info(&pdev->dev, "experimental PCI driver: removed command-restored=%d\n", !status && command == data->saved_command);
	kfree(data);
}

static int j71s_pci_test_probe(struct pci_dev *pdev, const struct pci_device_id *id)
{
	struct pci_host_bridge *host = pci_find_host_bridge(pdev->bus);
	struct j71s_pci_test_data *data;
	u16 command;
	u32 version;
	int ret;

	if (!host || !host->dev.parent || !host->dev.parent->of_node ||
	    !of_device_is_compatible(host->dev.parent->of_node, "orchard,j71s-pcie-diagnostic") ||
	    pci_resource_start(pdev, 0) != 0x7c0000000ULL || pci_resource_len(pdev, 0) != 0x4000)
		return -ENODEV;
	if (pci_read_config_word(pdev, PCI_COMMAND, &command) || (command & 6))
		return -EINVAL;
	data = kzalloc(sizeof(*data), GFP_KERNEL);
	if (!data)
		return -ENOMEM;
	data->saved_command = command;
	ret = pci_enable_device_mem(pdev);
	if (ret)
		goto out_free;
	data->bar = pci_iomap(pdev, 0, 0);
	if (!data->bar) {
		ret = -ENOMEM;
		goto out_disable;
	}
	version = readl(data->bar + 8);
	if (version != 0x10001) {
		ret = -EIO;
		goto out_unmap;
	}
	pci_set_drvdata(pdev, data);
	dev_info(&pdev->dev, "experimental PCI driver: bound version=%#x master-off=%d\n",
		 version, !(readw(((struct j71s_scan_state *)pdev->bus->sysdata)->ecam + 0x100004) & 4));
	return 0;
out_unmap:
	pci_iounmap(pdev, data->bar);
out_disable:
	pci_disable_device(pdev);
	pci_write_config_word(pdev, PCI_COMMAND, command);
out_free:
	kfree(data);
	return ret;
}

static const struct pci_device_id j71s_pci_test_ids[] = {
	{ PCI_DEVICE(0x106b, 0x2002) },
	{ }
};
static struct pci_driver j71s_pci_test_driver = {
	.name = "j71s-nvme-readonly-test",
	.id_table = j71s_pci_test_ids,
	.probe = j71s_pci_test_probe,
	.remove = j71s_pci_test_remove,
	.shutdown = j71s_pci_test_remove,
};

static int j71s_pcie_scan_once(struct device *dev)
{
	struct pci_host_bridge *bridge;
	struct j71s_scan_state *state;
	struct pci_dev *endpoint;
	bool test_driver_registered = false;
	u16 saved_root_cmd = 0;
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
	    (readw(state->ecam + 0x100004) & 6) || (readw(state->ecam + 4) & 6) ||
	    readl(state->ecam + 0x20) != 0) {
		ret = -EINVAL;
		goto out_free;
	}
	saved_root_cmd = readw(state->ecam + PCI_COMMAND);
	state->mem.name = "j71s temporary PCI memory";
	state->mem.start = 0x7c0000000ULL;
	state->mem.end = 0x7c00fffffULL;
	state->mem.flags = IORESOURCE_MEM;
	ret = request_resource(&iomem_resource, &state->mem);
	if (ret)
		goto out_free;
	writel(0xc000c000U, state->ecam + 0x20);
	if (readl(state->ecam + 0x20) != 0xc000c000U) {
		ret = -EIO;
		goto out_window;
	}
	pci_add_resource_offset(&bridge->windows, &state->mem, 0x700000000ULL);
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
		if (endpoint && endpoint->vendor == 0x106b && endpoint->device == 0x2002 &&
		    !endpoint->dev.driver && pci_resource_len(endpoint, 0) == 0x4000 &&
		    (pci_resource_flags(endpoint, 0) & IORESOURCE_MEM)) {
			int assigned;

			pci_bus_claim_resources(bridge->bus);
			assigned = pci_assign_resource(endpoint, 0);
			dev_info(dev, "experimental PCI assignment: ret=%d resource-start-ok=%d bar-ok=%d upper-zero=%d master-off=%d\n",
				 assigned, pci_resource_start(endpoint, 0) == 0x7c0000000ULL,
				 readl(state->ecam + 0x100010) == 0xc0000004U,
				 readl(state->ecam + 0x100014) == 0,
				 !(readw(state->ecam + 0x100004) & 4));
			if (!assigned && pci_resource_start(endpoint, 0) == 0x7c0000000ULL &&
			    pci_resource_len(endpoint, 0) == 0x4000) {
				int map_ret = j71s_pcie_test_iomap(dev, state, endpoint);
				dev_info(dev, "experimental PCI iomap: ret=%d\n", map_ret);
				if (!map_ret) {
					struct j71s_diag_work *ctx = dev_get_drvdata(dev);
					int driver_ret;

					saved_root_cmd = readw(state->ecam + PCI_COMMAND);
					writew(saved_root_cmd | PCI_COMMAND_MEMORY, state->ecam + PCI_COMMAND);
					if (readw(state->ecam + PCI_COMMAND) != (saved_root_cmd | PCI_COMMAND_MEMORY))
						goto no_hold;
					driver_ret = pci_register_driver(&j71s_pci_test_driver);
					if (driver_ret) {
						dev_err(dev, "experimental PCI driver: registration failed %d\n", driver_ret);
						goto no_hold;
					}
					test_driver_registered = true;
					pci_bus_add_devices(bridge->bus);
					dev_info(dev, "experimental PCI driver: binding=%d\n", endpoint->dev.driver == &j71s_pci_test_driver.driver);
					dev_info(dev, "experimental PCI hold: active until stop\n");
					pci_unlock_rescan_remove();
					wait_event(ctx->stop_wq, READ_ONCE(ctx->stop));
					pci_lock_rescan_remove();
					dev_info(dev, "experimental PCI hold: stop requested\n");
				}
			}
		}
no_hold:
		if (endpoint)
			pci_dev_put(endpoint);
		pci_stop_root_bus(bridge->bus);
		pci_remove_root_bus(bridge->bus);
		if (test_driver_registered)
			pci_unregister_driver(&j71s_pci_test_driver);
		writew(saved_root_cmd, state->ecam + PCI_COMMAND);
		dev_info(dev, "experimental PCI driver: root command restored=%d\n", readw(state->ecam + PCI_COMMAND) == saved_root_cmd);
	}
	pci_unlock_rescan_remove();
	writel(0, state->ecam + 0x100014);
	writel(4, state->ecam + 0x100010);
	dev_info(dev, "experimental PCI assignment: bars-restored=%d\n",
		 readl(state->ecam + 0x100010) == 4 && readl(state->ecam + 0x100014) == 0);
out_window:
	writel(0, state->ecam + 0x20);
	dev_info(dev, "experimental PCI assignment: window-restored=%d\n", readl(state->ecam + 0x20) == 0);
	if (release_resource(&state->mem)) {
		dev_err(dev, "experimental PCI assignment: retaining bridge after resource release failure\n");
		return -EBUSY;
	}
out_free:
	pci_free_host_bridge(bridge);
	return ret;
}
