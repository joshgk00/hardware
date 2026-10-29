/* SPDX-License-Identifier: GPL-2.0-only */
/* Candidate AIC vector allocation only: no IRQ handler or MSI is enabled. */
#include <linux/irqdomain.h>
#include <dt-bindings/interrupt-controller/apple-aic.h>
#include <dt-bindings/interrupt-controller/irq.h>
static int j71s_test_aic_vectors(struct device *dev, u32 first, u32 count)
{
 struct device_node *node;
 struct irq_fwspec spec = {};
 struct irq_domain *domain;
 unsigned int virq[8] = {}, i, allocated = 0, type;
 unsigned long hwirq;
 int ret = 0;

 if (!count || count > ARRAY_SIZE(virq) || first > U32_MAX - count)
  return -EINVAL;
 node = of_find_compatible_node(NULL, NULL, "apple,aic");
 if (!node)
  return -ENODEV;
 spec.fwnode = of_fwnode_handle(node);
 spec.param_count = 3;
 spec.param[0] = AIC_IRQ;
 spec.param[2] = IRQ_TYPE_EDGE_RISING;
 domain = irq_find_matching_fwspec(&spec, DOMAIN_BUS_WIRED);
 if (!domain || !domain->ops || !domain->ops->translate) {
  ret = -ENODEV;
  goto out;
 }
 for (i = 0; i < count; i++) {
  spec.param[1] = first + i;
  ret = domain->ops->translate(domain, &spec, &hwirq, &type);
  if (ret)
   break;
  if (type != IRQ_TYPE_EDGE_RISING || irq_find_mapping(domain, hwirq)) {
   ret = -EBUSY;
   break;
  }
  virq[i] = irq_create_fwspec_mapping(&spec);
  if (!virq[i]) {
   ret = -ENOSPC;
   break;
  }
  allocated++;
 }
 for (i = allocated; i > 0; i--)
  irq_dispose_mapping(virq[i - 1]);
 dev_info(dev, "experimental MSI AIC vectors: allocated=%u requested=%u ret=%d\n",
          allocated, count, ret);
out:
 of_node_put(node);
 return ret;
}
