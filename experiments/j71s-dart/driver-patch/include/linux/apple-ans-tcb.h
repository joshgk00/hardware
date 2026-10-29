/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef _LINUX_APPLE_ANS_TCB_H
#define _LINUX_APPLE_ANS_TCB_H

#include <linux/apple-ans.h>
#include <linux/errno.h>
#include <linux/kernel.h>
#include <linux/overflow.h>
#include <linux/string.h>

#define APPLE_ANS_TCB_BYTES 0x80
#define APPLE_ANS_FLATDMA_BASE 0x40000000ULL
#define APPLE_ANS_FLATDMA_STRIDE (8ULL * 1024 * 1024)

/* Pure descriptor preparation: does not arm or invalidate hardware. */
static inline int apple_ans_build_tcb(u32 *tcb, u32 *sgl, u64 sgl_base,
                                      unsigned int tag, const u64 *pages,
                                      unsigned int npages, dma_addr_t *iova)
{
 u64 offset, sgl_dma, end;
 unsigned int i;

 if (!tcb || !sgl || !pages || !npages ||
     tag >= APPLE_ANS_NVMMU_MAX_REQS || npages > APPLE_ANS_NVMMU_MAX_PAGES)
  return -EINVAL;
 for (i = 0; i < npages; i++)
  if (!IS_ALIGNED(pages[i], APPLE_ANS_NVMMU_PAGE_SIZE) ||
      (pages[i] >> 12) > U32_MAX)
   return -EINVAL;
 offset = (u64)tag * APPLE_ANS_NVMMU_MAX_PAGES * sizeof(*sgl);
 if (check_add_overflow(sgl_base, offset, &sgl_dma) ||
     check_add_overflow(sgl_dma,
                        (u64)APPLE_ANS_NVMMU_MAX_PAGES * sizeof(*sgl) - 1, &end))
  return -EOVERFLOW;
 memset(tcb, 0, APPLE_ANS_TCB_BYTES);
 memset(sgl, 0, APPLE_ANS_NVMMU_MAX_PAGES * sizeof(*sgl));
 tcb[0] = 0x100 | 0x200;
 tcb[1] = npages;
 tcb[2] = pages[0] >> 12;
 for (i = 0; i < npages; i++)
  sgl[i] = pages[i] >> 12;
 memcpy(&tcb[4], &sgl_dma, sizeof(sgl_dma));
 if (iova)
  *iova = APPLE_ANS_FLATDMA_BASE + tag * APPLE_ANS_FLATDMA_STRIDE;
 return 0;
}
#endif
