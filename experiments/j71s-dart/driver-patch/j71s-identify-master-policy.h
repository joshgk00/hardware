/* SPDX-License-Identifier: GPL-2.0-only */
/* Pure write-policy check: no PCI configuration writes are performed here. */
static bool j71s_identify_master_allowed(bool opted_in, bool used, bool armed,
                  bool descriptor_published, bool scratch_ready, bool locked,
                  unsigned int bus, unsigned int devfn, unsigned int where,
                  int size, u32 identity, u16 saved_command, u32 requested)
{
 const u16 permitted = PCI_COMMAND_MEMORY | PCI_COMMAND_INTX_DISABLE;

 return opted_in && !used && armed && descriptor_published && scratch_ready && locked &&
        bus == 1 && devfn == 0 && where == PCI_COMMAND && size == 2 &&
        identity == 0x2002106bU && (saved_command & PCI_COMMAND_MEMORY) &&
        !(saved_command & ~permitted) && requested == (saved_command | PCI_COMMAND_MASTER);
}
