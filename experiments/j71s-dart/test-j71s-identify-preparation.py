#!/usr/bin/env python3
"""Exercise the command bytes and overflow-safe DMA window checks."""
from pathlib import Path
import subprocess
import tempfile
src=(Path(__file__).parent/'driver-patch/j71s-identify-preparation.h').read_text()
window=src[src.index('static bool j71s_identify_window_contains'):src.index('/* Call only before')]
preamble=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
typedef uint64_t dma_addr_t;
#define J71S_IDENTIFY_IOVA_FIRST 0x80000000ULL
#define J71S_IDENTIFY_IOVA_END 0xbc000000ULL
#define J71S_IDENTIFY_FLATDMA 0x40000000ULL
#define BIT(n) (1U << (n))
#define SZ_4K 4096ULL
#define DMA_BIT_MASK(n) ((1ULL<<(n))-1)
#define NVME_IDENTIFY_DATA_SIZE 4096
#define IS_ALIGNED(a,n) (((a)&((n)-1))==0)
typedef uint64_t u64;
#define cpu_to_le16(x) (x)
#define cpu_to_le64(x) (x)
#define nvme_admin_identify 6
#define NVME_ID_CNS_CTRL 1
struct nvme_command { struct { uint8_t opcode, flags; uint16_t command_id; uint32_t nsid; uint64_t reserved[2]; struct { uint64_t prp1, prp2; } dptr; uint8_t cns; uint8_t rest[23]; } identify; };
'''
checks=r'''
int main(void) {
 struct nvme_command c; unsigned char *b=(void *)&c;
 memset(&c, 0xff, sizeof(c)); j71s_identify_build_command(&c);
 if (sizeof(c)!=64 || b[0]!=6 || b[1]!=0x20 || b[2]!=1 || b[3]!=0 ||
     b[24]!=0 || b[25]!=0 || b[26]!=0 || b[27]!=0x40 || b[40]!=1) abort();
 for (int i=0;i<64;i++) if(i!=0&&i!=1&&i!=2&&i!=27&&i!=40&&b[i]) abort();
 if (!j71s_identify_payload_physical_valid(0x100000) ||
     !j71s_identify_payload_physical_valid((1ULL<<36)-4096) ||
     j71s_identify_payload_physical_valid(0x100001) ||
     j71s_identify_payload_physical_valid(1ULL<<36) ||
     j71s_identify_payload_physical_valid(UINT64_MAX)) abort();
 if (!j71s_identify_window_contains(0x80000000,16384) ||
     !j71s_identify_window_contains(0xbbffc000,16384) ||
     j71s_identify_window_contains(0x7fffffff,1) ||
     j71s_identify_window_contains(0xbc000000,1) ||
     j71s_identify_window_contains(0xbbffc001,16384) ||
     j71s_identify_window_contains(UINT64_MAX,2) ||
     j71s_identify_window_contains(0x80000000,0)) abort();
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'test.c').write_text(preamble+window+checks)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('Identify command bytes and DMA window bounds passed.')
