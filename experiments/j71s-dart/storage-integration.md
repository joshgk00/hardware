# J71s storage integration: current boundaries

The J71s PCI diagnostic has enumerated the Apple storage endpoint and mapped
its BAR, but it is not a storage driver. This note records source-level
integration requirements; none of the untested steps below is evidence of
working DMA or disk I/O.

## Address paths

The J71b H9P implementation allocates its NVMMU TCB, TCB table and SGL using
the PCI host platform device's DMA API. It programs their DMA addresses into
the storage-port NVMMU, while its SART-style scratch window is configured
from a reserved physical region and an explicitly chosen controller IOVA.
The ANS request path separately maps request pages with the endpoint's DMA
API and constructs FlatDMA entries from physical page addresses. These are
separate address domains; neither the host allocation test nor an endpoint
allocation proves the other device's translation or that the NVMMU can fetch
tables. The meaning of these paths on S8000 still needs hardware validation.

The present J71s overlay disables the DART and the earlier software consumer.
The previous software-only DART map test validated page-table bookkeeping with
its own power/control sequence, not simultaneous operation with the PCI host.
A combined design needs explicit ownership and ordering for shared PCIe power,
clocks, reset and DART registration, followed by verification that the intended
PCI requester is attached to the correct stream. Register readbacks and
`iommu_iova_to_phys()` do not prove a physical transfer.

## Host-driver integration

The active diagnostic host intentionally allows only endpoint BAR sizing,
assignment and memory-only command writes. The actual ANS preinitialization
also writes the latency timer and configuration offsets 0x17c, 0x18c and
0x188; a real controller also needs bus mastering. These writes are rejected
by the current policy, as checked by `test-j71s-ans-config-policy.py`.
The diagnostic also lacks the H9P host's MSI domain and interrupt setup.
Consequently attaching the existing NVMe driver to this host cannot be treated
as an installation attempt. A production host needs normal PCI configuration,
verified DMA/IOMMU attachment, interrupts and lifecycle handling rather than
simply removing these safeguards.

Before issuing commands, a combined implementation must establish ownership
and teardown of DMA buffers and translation tables across failures, reset,
unbind and kexec; prevent freeing memory while hardware can still access it;
and verify the S8000 port and controller configuration against the device.
The eventual test needs observable controller DMA and a bounded, read-only
storage command before any installer or write operation. MSI delivery and
error handling need separate verification. No disk command has been executed
in the diagnostic to date.

## Upstream initialization comparison

In hardware main `0cfb171`, the S8003 path waits for its candidate invalidate
FIFO to drain, explicitly writes zero to SART control, performs `dma_wmb()`,
and programs the table address before the TCB base. The isolated J71s TCB
initialization helper already checks its candidate FIFO, issues `dma_wmb()`
and programs the table before the base; it checks that SART is zero but does
not explicitly write zero. The physical no-doorbell test reached the guard and
returned without a command. The helper's host mock passed again, including
invalid and nonempty FIFO cases, but it cannot validate physical ordering,
register semantics or DMA. An explicit SART-zero write remains an untested
sequence difference; neither a redundant write nor the S8003 meaning can be
assumed safe on S8000. The earlier disconnected command tests do not isolate
this difference.
