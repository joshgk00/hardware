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
assignment and memory-only command writes. The upstream ANS preinitialization
also writes the latency timer and discovers LTR and L1SS capability registers
before configuring them; earlier J71s observations placed candidate registers
at 0x17c, 0x18c and 0x188. A real controller also needs bus mastering. These writes are rejected
by the current policy, as checked by `test-j71s-ans-config-policy.py`.
The diagnostic also lacks the H9P host's MSI domain and interrupt setup.
Consequently attaching the existing NVMe driver to this host cannot be treated
as an installation attempt. A production host needs normal PCI configuration,
verified DMA/IOMMU attachment, interrupts and lifecycle handling rather than
simply removing these safeguards.

The upstream ANS integration has an additional selection boundary: in the
tested `0cfb171` kernel, `nvme_pci_apple_ans_hosts` names only S8003 and T8010
host compatibles. Its patch explicitly leaves `apple,s8000-pcie` out because
there is no binding. The PCI NVMe driver selects Apple ANS DMA operations and
quirks through that host match. Thus a future S8000 host description alone
would not select this glue under that compatible; S8000 binding and matching
need design and validation alongside the actual DMA and interrupt work. This
is not evidence that adding a compatible or borrowing S8003 quirks is safe.

The upstream H9P PCIe host driver's own device match table likewise has no
S8000 compatible. Its S8003 match selects SoC-specific initialization,
tunables and NVMMU behavior. Supporting J71s therefore needs a validated host
binding and match data as well as ANS selection; simply describing an S8000
node would not bind this driver, and claiming S8003 compatibility without
evidence could apply the wrong hardware sequence.

For the related Wi-Fi path, the saved private J71s ADT has the WLAN reg-on and
interrupt properties and the PCIe port-1 CLKREQ, device-wake and PERST
properties. As a preliminary comparison, each corresponding raw property
contains the same little-endian integer used for that signal in the upstream
J71t tree. This is only a raw-value comparison, not full property decoding or
proof of wiring, polarity, electrical sequencing or functional Wi-Fi. The
J71s root-complex and port-1 path still need independent validation.

The local ADT parser's function-record layout identifies the first word as a
phandle and the words after its four-character function name as arguments.
On that basis, each of the four J71s WLAN function properties has the J71t
candidate pin as its first argument. Their phandles resolve to the PMIC for
reg-on and the SoC GPIO node for CLKREQ, device-wake and PERST; the first
interrupt word also matches the J71t candidate. This strengthens the source
comparison, but does not decode the remaining arguments or prove polarity,
timing, actual electrical behavior or functional Wi-Fi.

`check-wlan-signals.py` repeats this comparison locally with the unified
Orchard ADT parser and prints only match status. It rejects duplicate selected
paths, ambiguous phandles and invalid function-record lengths; it does not print
the private tree or access hardware. Run it with the Orchard `src` directory
on `PYTHONPATH` and the private ADT path as its argument. Synthetic tests cover
matching records and several malformed or ambiguous inputs. The real J71s
snapshot matched all seven checks; the same physical limitations apply.

The saved J71s UART2 transmit and RTS function records also resolve to the
SoC GPIO node and have first arguments matching the corresponding J71t WLAN
UART pin candidates. Their remaining arguments, electrical operation and the
upstream WLAN UART integration have not been validated on J71s.

Both saved J71s WLAN nodes include `4355` in their compatible data, consistent
with the BCM4355 family named by the J71s firmware recipe and J71t tree. The
checked compatible data did not itself contain the candidate PCI device ID or
the `4355c0` revision string. This is family-level source evidence only; actual
PCI enumeration and firmware selection remain unverified.

Before issuing commands, a combined implementation must establish ownership
and teardown of DMA buffers and translation tables across failures, reset,
unbind and kexec; prevent freeing memory while hardware can still access it;
and verify the S8000 port and controller configuration against the device.
The eventual test needs observable controller DMA and a bounded, read-only
storage command before any installer or write operation. MSI delivery and
error handling need separate verification. Earlier command attempts lost the
diagnostic connection before a doorbell return or completion was observed;
whether the controller received a command is unknown, and no successful disk
command has been demonstrated.

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

The current upstream PCI ANS path also invokes a DMA-slot reset before enabling
the controller and explicitly writes zero to the controller's regular-init
register at `0x1800` before writing its host-memory-buffer registers. The J71s
one-shot scratch helper checks that `0x1800` reads zero and programs its
scratch registers, but does not make that explicit init-register write; its
bounded path does not reproduce the upstream full slot-reset sequence. These
are further source-level differences, not a demonstrated cause of the failed
command. The effects of those writes and invalidations on S8000 remain
unverified; no such hardware action was performed in this comparison.
