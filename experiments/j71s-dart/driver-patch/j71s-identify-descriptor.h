/* SPDX-License-Identifier: GPL-2.0-only */
/* Prepares tag zero for a retained one-shot Identify payload. */
#include <linux/apple-ans-tcb.h>
#include <linux/scatterlist.h>

struct j71s_identify_descriptor {
 u32 *tcb;
 u32 *sgl;
 dma_addr_t sgl_dma;
 bool published;
};

/* tcb must refer to slot zero in a retained, initialized host NVMMU table.
 * The caller retains host, tcb and the returned SGL until physical reset.
 * This prepares memory only; it does not enable DMA or submit the command.
 */
static int __maybe_unused j71s_identify_prepare_descriptor(struct device *host,
                         struct j71s_identify_preparation *p, u32 *tcb,
                         struct j71s_identify_descriptor *d)
{
 struct sg_table table;
 dma_addr_t flat;
 u64 page;
 int ret;
 bool identity;

 if (!host || !p || !p->payload || p->armed || p->descriptor_published || !tcb || !d ||
     d->published || d->sgl || !j71s_test_kexec_locked())
  return -EINVAL;
 d->sgl = dma_alloc_coherent(host, PAGE_SIZE, &d->sgl_dma, GFP_KERNEL | __GFP_ZERO);
 if (!d->sgl)
  return -ENOMEM;
 if (!IS_ALIGNED(d->sgl_dma, SZ_4K) ||
     d->sgl_dma > DMA_BIT_MASK(36) - (PAGE_SIZE - 1)) {
  ret = -ERANGE;
  goto free_sgl;
 }
 ret = dma_get_sgtable(host, &table, d->sgl, d->sgl_dma, PAGE_SIZE);
 if (ret)
  goto free_sgl;
 identity = table.nents == 1 && table.sgl->length >= PAGE_SIZE &&
            sg_phys(table.sgl) == d->sgl_dma;
 sg_free_table(&table);
 if (!identity) {
  ret = -ERANGE;
  goto free_sgl;
 }
 page = p->payload_phys;
 ret = apple_ans_build_tcb(tcb, d->sgl, d->sgl_dma, 0, &page, 1,
                           APPLE_ANS_TCB_WRITE, &flat);
 if (ret)
  goto free_sgl;
 /* Do not free this SGL or payload after publishing the valid TCB count. */
 d->tcb = tcb;
 d->published = true;
 p->descriptor_published = true;
 if (flat != J71S_IDENTIFY_FLATDMA)
  return -EIO;
 return 0;
free_sgl:
 dma_free_coherent(host, PAGE_SIZE, d->sgl, d->sgl_dma);
 d->sgl = NULL;
 d->sgl_dma = 0;
 return ret;
}
