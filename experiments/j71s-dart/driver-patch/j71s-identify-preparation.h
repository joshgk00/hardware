/* SPDX-License-Identifier: GPL-2.0-only */
/* Software preparation only: does not enable the device or submit a command. */
#include <linux/dma-mapping.h>
#include <linux/nvme.h>
#include <linux/scatterlist.h>
#include <linux/sizes.h>

#define J71S_IDENTIFY_QUEUE_DEPTH 16
#define J71S_IDENTIFY_IOVA_FIRST 0x80000000ULL
#define J71S_IDENTIFY_IOVA_END 0xbc000000ULL
#define J71S_IDENTIFY_FLATDMA 0x40000000ULL

struct j71s_identify_preparation {
 struct nvme_command *sq;
 struct nvme_completion *cq;
 void *payload;
 dma_addr_t sq_dma, cq_dma, payload_dma;
 phys_addr_t payload_phys;
 bool armed; /* Irreversible in this experiment: physical reset required. */
 bool descriptor_published;
};

static bool j71s_identify_window_contains(dma_addr_t addr, size_t size)
{
 return size && addr >= J71S_IDENTIFY_IOVA_FIRST &&
        addr < J71S_IDENTIFY_IOVA_END && size <= J71S_IDENTIFY_IOVA_END - addr;
}

static void j71s_identify_build_command(struct nvme_command *cmd)
{
 memset(cmd, 0, sizeof(*cmd));
 cmd->identify.opcode = nvme_admin_identify;
 cmd->identify.flags = BIT(5); /* Candidate Apple FlatDMA flag. */
 cmd->identify.command_id = cpu_to_le16(1);
 cmd->identify.dptr.prp1 = cpu_to_le64(J71S_IDENTIFY_FLATDMA);
 cmd->identify.cns = NVME_ID_CNS_CTRL;
}

/* Call only before any of these addresses have been given to hardware. */
static int __maybe_unused j71s_identify_release_unarmed(struct device *dev,
                                                   struct j71s_identify_preparation *p)
{
 if (p->armed || p->descriptor_published)
  return -EBUSY;
 if (p->payload) dma_free_coherent(dev, PAGE_SIZE, p->payload, p->payload_dma);
 if (p->cq) dma_free_coherent(dev, PAGE_SIZE, p->cq, p->cq_dma);
 if (p->sq) dma_free_coherent(dev, PAGE_SIZE, p->sq, p->sq_dma);
 memset(p, 0, sizeof(*p));
 return 0;
}

static int __maybe_unused j71s_identify_prepare(struct device *dev,
                                                struct j71s_identify_preparation *p)
{
 struct sg_table sgt;
 struct nvme_command *cmd;
 int ret = -ENOMEM;

 BUILD_BUG_ON(J71S_IDENTIFY_QUEUE_DEPTH * sizeof(struct nvme_command) > PAGE_SIZE);
 BUILD_BUG_ON(J71S_IDENTIFY_QUEUE_DEPTH * sizeof(struct nvme_completion) > PAGE_SIZE);
 /* Caller supplies a zero-initialized context; never reset a published one. */
 if (!dev || !p || p->armed || p->descriptor_published)
  return -EBUSY;
 memset(p, 0, sizeof(*p));
 p->sq = dma_alloc_coherent(dev, PAGE_SIZE, &p->sq_dma, GFP_KERNEL | __GFP_ZERO);
 p->cq = dma_alloc_coherent(dev, PAGE_SIZE, &p->cq_dma, GFP_KERNEL | __GFP_ZERO);
 p->payload = dma_alloc_coherent(dev, PAGE_SIZE, &p->payload_dma, GFP_KERNEL | __GFP_ZERO);
 if (!p->sq || !p->cq || !p->payload)
  goto fail;
 ret = -ERANGE;
 if (!IS_ALIGNED(p->sq_dma, PAGE_SIZE) || !IS_ALIGNED(p->cq_dma, PAGE_SIZE) ||
     !j71s_identify_window_contains(p->sq_dma, PAGE_SIZE) ||
     !j71s_identify_window_contains(p->cq_dma, PAGE_SIZE) ||
     !j71s_identify_window_contains(p->payload_dma, PAGE_SIZE))
  goto fail;
 ret = dma_get_sgtable(dev, &sgt, p->payload, p->payload_dma, PAGE_SIZE);
 if (ret)
  goto fail;
 if (sgt.nents != 1 || sgt.sgl->length < PAGE_SIZE) {
  sg_free_table(&sgt);
  ret = -EINVAL;
  goto fail;
 }
 p->payload_phys = sg_phys(sgt.sgl);
 sg_free_table(&sgt);
 ret = -ERANGE;
 if (!IS_ALIGNED(p->payload_phys, SZ_4K) || (p->payload_phys >> 12) > U32_MAX)
  goto fail;
 cmd = &p->sq[0];
 j71s_identify_build_command(cmd);
 dma_wmb();
 return 0;
fail:
 j71s_identify_release_unarmed(dev, p);
 return ret;
}
