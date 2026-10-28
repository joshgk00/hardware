/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef _LINUX_APPLE_S8000_TUNABLE_MMIO_H
#define _LINUX_APPLE_S8000_TUNABLE_MMIO_H

#include <linux/apple-s8000-tunables.h>
#include <linux/io.h>
#include <linux/limits.h>

/* Tables must already be validated and saved[] must have count entries. */
static inline int apple_s8000_apply_tunables(void __iomem *base,
		const struct apple_s8000_tunable *table, unsigned int count,
		u32 *saved, unsigned int *applied)
{
	if (*applied)
		return -EINVAL;
	while (*applied < count) {
		unsigned int i = *applied;
		u32 old = readl(base + table[i].offset);
		u32 value;

		if (old == U32_MAX)
			return -EIO;
		saved[i] = old;
		value = (old & ~table[i].mask) | table[i].value;
		writel(value, base + table[i].offset);
		(*applied)++;
		if (readl(base + table[i].offset) != value)
			return -EIO;
	}
	return 0;
}

/* Restore in reverse order, including the record whose readback failed. */
static inline unsigned int apple_s8000_restore_tunables(void __iomem *base,
		const struct apple_s8000_tunable *table, const u32 *saved,
		unsigned int *applied)
{
	unsigned int errors = 0;

	while (*applied) {
		unsigned int i = --*applied;

		writel(saved[i], base + table[i].offset);
		if (readl(base + table[i].offset) != saved[i])
			errors++;
	}
	return errors;
}
#endif
