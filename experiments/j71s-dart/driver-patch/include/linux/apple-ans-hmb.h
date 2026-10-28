/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef _LINUX_APPLE_ANS_HMB_H
#define _LINUX_APPLE_ANS_HMB_H

#include <linux/errno.h>
#include <linux/ioport.h>
#include <linux/limits.h>
#include <linux/of.h>
#include <linux/of_address.h>
#include <linux/of_reserved_mem.h>

/* The dynamic no-map region is owned by reserved-memory for the entire boot. */
static inline int apple_ans_hmb_resource(struct device_node *node,
					struct resource *res)
{
	struct reserved_mem *rmem;

	if (of_find_property(node, "reg", NULL))
		return of_address_to_resource(node, 0, res);
	if (!of_property_read_bool(node, "no-map") ||
	    of_property_read_bool(node, "reusable"))
		return -EINVAL;
	rmem = of_reserved_mem_lookup(node);
	if (!rmem || !rmem->size || rmem->base > RESOURCE_SIZE_MAX ||
	    rmem->size - 1 > RESOURCE_SIZE_MAX - rmem->base)
		return -EINVAL;
	res->start = rmem->base;
	res->end = rmem->base + rmem->size - 1;
	res->flags = IORESOURCE_MEM;
	return 0;
}
#endif
