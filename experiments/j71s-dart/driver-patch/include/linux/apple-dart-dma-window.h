/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef _LINUX_APPLE_DART_DMA_WINDOW_H
#define _LINUX_APPLE_DART_DMA_WINDOW_H

#include <linux/errno.h>
#include <linux/kernel.h>
#include <linux/log2.h>
#include <linux/overflow.h>
#include <linux/types.h>

/* Validate an offset-based IOVA window before using ~start as a DART mask. */
static inline int apple_dart_validate_window(u64 start, u64 length, u32 pgsize,
                                              u32 ias, u64 *end)
{
 u64 last, max;
 if (!end || !length || !is_power_of_2(pgsize) || !ias || ias > 63 ||
     !IS_ALIGNED(start, pgsize) || !IS_ALIGNED(length, pgsize) ||
     (start && !is_power_of_2(start)) ||
     check_add_overflow(start, length - 1, &last))
  return -EINVAL;
 max = (1ULL << ias) - 1;
 if (last > max || (start && ((last & start) != start || last >= 2 * start)))
  return -EINVAL;
 *end = last;
 return 0;
}
#endif
