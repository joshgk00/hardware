/* SPDX-License-Identifier: GPL-2.0-only */
/* Temporary port-0 MSI domain. Controller IRQ delivery remains unverified. */
#include <linux/bitmap.h>
#include <linux/msi.h>
#include <linux/irqchip.h>
#include <linux/irqchip/irq-msi-lib.h>

struct j71s_msi_test {
 struct irq_domain *domain;
 struct irq_fwspec parent_spec;
 spinlock_t lock;
 unsigned long used;
 u64 doorbell;
};

static void j71s_msi_compose(struct irq_data *data, struct msi_msg *msg)
{
 struct j71s_msi_test *ctx = irq_data_get_irq_chip_data(data);
 msg->address_lo = lower_32_bits(ctx->doorbell);
 msg->address_hi = upper_32_bits(ctx->doorbell);
 msg->data = data->hwirq;
}

static struct irq_chip j71s_msi_chip = {
 .name = "J71s experimental PCI MSI",
 .irq_mask = irq_chip_mask_parent,
 .irq_unmask = irq_chip_unmask_parent,
 .irq_eoi = irq_chip_eoi_parent,
 .irq_set_affinity = irq_chip_set_affinity_parent,
 .irq_compose_msi_msg = j71s_msi_compose,
};

static int j71s_msi_alloc(struct irq_domain *domain, unsigned int virq,
                          unsigned int nr_irqs, void *arg)
{
 struct j71s_msi_test *ctx = domain->host_data;
 struct irq_fwspec spec = ctx->parent_spec;
 msi_alloc_info_t *info = arg;
 struct msi_desc *desc = info ? info->desc : NULL;
 struct device *dev = desc ? msi_desc_to_dev(desc) : NULL;
 unsigned long flags;
 unsigned int slot;
 int ret;

 if (nr_irqs != 1 || !dev || !dev_is_pci(dev) || !to_pci_dev(dev)->bus ||
     to_pci_dev(dev)->bus->number != 1 || to_pci_dev(dev)->devfn != 0)
  return -ENOSPC;
 spin_lock_irqsave(&ctx->lock, flags);
 slot = find_first_zero_bit(&ctx->used, 8);
 if (slot == 8) {
  spin_unlock_irqrestore(&ctx->lock, flags);
  return -ENOSPC;
 }
 __set_bit(slot, &ctx->used);
 spin_unlock_irqrestore(&ctx->lock, flags);
 spec.param[1] += slot;
 ret = irq_domain_alloc_irqs_parent(domain, virq, 1, &spec);
 if (ret) {
  spin_lock_irqsave(&ctx->lock, flags);
  __clear_bit(slot, &ctx->used);
  spin_unlock_irqrestore(&ctx->lock, flags);
  return ret;
 }
 irq_domain_set_hwirq_and_chip(domain, virq, slot, &j71s_msi_chip, ctx);
 return 0;
}

static void j71s_msi_free(struct irq_domain *domain, unsigned int virq,
                          unsigned int nr_irqs)
{
 struct irq_data *data = irq_domain_get_irq_data(domain, virq);
 struct j71s_msi_test *ctx = domain->host_data;
 unsigned long flags;
 irq_hw_number_t slot;

 if (!data || nr_irqs != 1 || data->hwirq >= 8)
  return;
 slot = data->hwirq;
 irq_domain_free_irqs_parent(domain, virq, nr_irqs);
 spin_lock_irqsave(&ctx->lock, flags);
 __clear_bit(slot, &ctx->used);
 spin_unlock_irqrestore(&ctx->lock, flags);
}

static const struct irq_domain_ops j71s_msi_ops = {
 .alloc = j71s_msi_alloc, .free = j71s_msi_free,
};
static const struct msi_parent_ops j71s_msi_parent_ops = {
 .supported_flags = MSI_GENERIC_FLAGS_MASK,
 .required_flags = MSI_FLAG_USE_DEF_DOM_OPS | MSI_FLAG_USE_DEF_CHIP_OPS |
                   MSI_FLAG_PCI_MSI_MASK_PARENT,
 .chip_flags = MSI_CHIP_FLAG_SET_EOI,
 .bus_select_token = DOMAIN_BUS_PCI_MSI,
 .init_dev_msi_info = msi_lib_init_dev_msi_info,
};

static int j71s_msi_test_create(struct device *dev, struct j71s_msi_test *ctx,
                                u32 first, u64 doorbell)
{
 struct device_node *aic;
 struct irq_domain_info info = {
  .fwnode = dev_fwnode(dev), .ops = &j71s_msi_ops,
  .size = 8, .host_data = ctx,
 };

 if (!doorbell || !IS_ALIGNED(doorbell, SZ_4K) || first > U32_MAX - 7)
  return -EINVAL;
 aic = of_find_compatible_node(NULL, NULL, "apple,aic");
 if (!aic)
  return -ENODEV;
 ctx->parent_spec.fwnode = of_fwnode_handle(aic);
 ctx->parent_spec.param_count = 3;
 ctx->parent_spec.param[0] = AIC_IRQ;
 ctx->parent_spec.param[1] = first;
 ctx->parent_spec.param[2] = IRQ_TYPE_EDGE_RISING;
 info.parent = irq_find_matching_fwspec(&ctx->parent_spec, DOMAIN_BUS_WIRED);
 spin_lock_init(&ctx->lock);
 ctx->doorbell = doorbell;
 if (!info.parent) {
  of_node_put(aic);
  return -ENODEV;
 }
 ctx->domain = msi_create_parent_irq_domain(&info, &j71s_msi_parent_ops);
 of_node_put(aic);
 return ctx->domain ? 0 : -ENOMEM;
}
