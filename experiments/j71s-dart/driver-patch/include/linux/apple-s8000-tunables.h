/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef _LINUX_APPLE_S8000_TUNABLES_H
#define _LINUX_APPLE_S8000_TUNABLES_H

#include <linux/errno.h>
#include <linux/of.h>
#include <linux/types.h>

struct apple_s8000_tunable {
	u32 offset;
	u32 mask;
	u32 value;
};

/* Read and validate a complete table before the caller performs any MMIO. */
static inline int apple_s8000_read_tunables(struct device_node *node,
		const char *property, struct apple_s8000_tunable *out,
		unsigned int count, u32 window_size)
{
	unsigned int i;
	int ret;

	if (!count || count > 256 || window_size < 4 ||
	    of_property_count_u32_elems(node, property) != (int)(count * 3))
		return -EINVAL;
	for (i = 0; i < count; i++) {
		ret = of_property_read_u32_index(node, property, i * 3,
					 &out[i].offset);
		ret |= of_property_read_u32_index(node, property, i * 3 + 1,
					  &out[i].mask);
		ret |= of_property_read_u32_index(node, property, i * 3 + 2,
					  &out[i].value);
		if (ret || (out[i].offset & 3) ||
		    out[i].offset > window_size - 4 ||
		    (out[i].value & ~out[i].mask))
			return -EINVAL;
	}
	return 0;
}
#endif
