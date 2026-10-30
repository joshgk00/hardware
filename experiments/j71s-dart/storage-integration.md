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

The upstream S8003 device-tree source explicitly distinguishes its `phy-ip`
register window from S8000, which it says has no such region. In the saved
J71s ADT's raw PCIe `reg` words, the upstream S8003 `phy-ip` base was not
present. The S8003 host match sets `has_phy` and its setup uses that window,
so a J71s implementation cannot assume the S8003 resource layout unchanged.
The raw-word search alone does not establish translated address layout or
prove that any other register is safe to access.

Decoding the saved J71s PCIe `reg` property as 64-bit address/size pairs found
exact counterparts for the upstream S8003 configuration, root-complex, PHY,
port 0, port 1 and NVMMU ranges; the S8003 `phy-ip` range was absent from those
raw pairs. This supports a narrower resource-layout comparison than a blind
copy of S8003. It does not prove address translation, register semantics,
required power state or that port-1 accesses are safe.

Upstream S8003 deliberately brings up storage port 0 first and leaves other
ports off if it fails: its source explains that PCI bus numbering otherwise
could route the next port through the storage port's DART mapping. Endpoint
power and late enumeration are separately sequenced. A J71s Wi-Fi-only probe
must therefore explicitly establish port-to-bus and IOMMU routing rather than
assuming upstream port-1 mappings remain valid when port 0 is absent. The
S8003 rule is a design warning and does not prove S8000's mappings or behavior.

In the saved private J71s ADT, the `function-dart_force_active` phandles for
PCIe ports 0 and 1 resolve to `dart-apcie0` and `dart-apcie1` respectively.
This is evidence that the original device description associates separate DART
nodes with the two ports. It does not establish Linux requester IDs, stream
IDs, actual isolation or the correct `iommu-map`; those still need validation.

The saved WLAN endpoint's `iommu-parent` also matches the port-1 DART mapper's
phandle. The two DART nodes have identical raw `vm-offset` properties but
different `vm-size` properties on this iPad; their mapper `reg` properties
match. This rules out treating the two saved window descriptions as identical.
The meanings of the mapper value and window properties in Linux, their relation
to PCI requester IDs, and real DMA behavior remain unverified.
The saved WLAN `iommu-parent` property contains only the four-byte phandle;
the storage endpoint's property is twelve bytes. The existing port-0 window
extractor requires the latter format and an exact provisional storage window,
so it cannot be reused for port 1 without a separately justified decoder and
validation of the different window size.

For this J71s snapshot, each DART's first saved `vm-offset` word and `vm-size`
match the corresponding start and size encoded in the upstream S8003
`iommu-map` (including its different port-1 size). This is a comparison of
selected raw fields only; it does not establish how the second offset, mapper
record or S8000 requester and stream IDs should be translated into a Linux
mapping. The S8003 mapping must not be applied solely on this basis.

The two saved J71s DART `reg` records, decoded as 64-bit address and size,
match the corresponding S8003 DART addresses and 0x4000-byte sizes, and both
saved mapper `reg` values are zero. This is further source-level similarity;
it does not prove stream IDs, register semantics, isolation or safe DMA.
For both saved J71s DART nodes, the first 64-bit error-reflector word and the
32-bit fetch and diagnostic configuration values also match the corresponding
upstream S8003 properties. The remaining error-reflector data and any
runtime sequencing were not validated by that comparison.

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
reg-on and the SoC GPIO node for CLKREQ, device-wake and PERST; the two-word
interrupt record also matches the J71t ADT tuple documented upstream. This
strengthens the source comparison, but does not decode the remaining arguments or prove polarity,
timing, actual electrical behavior or functional Wi-Fi.

`check-wlan-signals.py` repeats this comparison locally with the unified
Orchard ADT parser and prints only match status. It rejects duplicate selected
paths, ambiguous phandles and invalid function-record lengths; it does not print
the private tree or access hardware. Run it with the Orchard `src` directory
on `PYTHONPATH` and the private ADT path as its argument. Synthetic tests cover
matching records and several malformed or ambiguous inputs. The real J71s
snapshot matched all sixteen checks, including port-to-DART references, the
WLAN mapper, selected window fields and DART register and initialization
candidates; the same physical limitations apply.

The saved J71s UART2 transmit and RTS function records also resolve to the
SoC GPIO node and have first arguments matching the corresponding J71t WLAN
UART pin candidates. Their remaining arguments, electrical operation and the
upstream WLAN UART integration have not been validated on J71s.

Both saved J71s WLAN nodes include `4355` in their compatible data, consistent
with the BCM4355 family named by the J71s firmware recipe and J71t tree. The
checked compatible data did not itself contain the candidate PCI device ID or
the `4355c0` revision string. This is family-level source evidence only; actual
PCI enumeration and firmware selection remain unverified.

The saved J71s ADT has both port-0 and port-1 configuration and root-port
tuning tables. For this one device, the corresponding port-0 and port-1 raw
tables are byte-identical (six configuration records and two root-port
records). This is a useful lead for a separate port-1 experiment, not proof
that other port settings, power sequencing, DMA, or Wi-Fi are interchangeable.
The raw device-derived tables remain private and have not been applied to
port 1 in the current desktop boot.

An offline comparison against the tested upstream S8003 driver's literal
tunable arrays found the J71s common table (34 records) and port-1 block table
(six records) matched in order. The two-record root-port configuration table
was not identical, and none of the four S8003 PHY-array records appeared as an
identical tuple in the 41-record J71s PHY table. This compares literal
offset/mask/value tuples only, not complete initialization sequences or MMIO
semantics. In particular, it is evidence against assuming the S8003 tables
can simply be reused wholesale for S8000.

In that literal comparison, both S8003 root-port offsets and masks appeared in
the J71s table, but only one complete tuple matched. None of the four S8003 PHY
offsets appeared in the saved J71s PHY table. These counts do not prove that
the blocks have equivalent address bases or that any differing value is safe;
register mapping and the device-specific sequence still require validation.
The difference is in the second root-port record in the compared order; its
offset and mask match the second upstream S8003 record, while its value does
not. Earlier J71s link diagnostics applied the J71s root-port records from
the private tree. That observation supports testing the J71s-specific values
in a future integration, but it does not validate a full PCIe host or DMA.

The offline `extract-pcie-tunables.py` converter now accepts `--port 1`, while
retaining port 0 as its default. On the saved private J71s ADT it validated
and emitted all four candidate tables to a mode-0600 private fragment, and a
synthetic DTS containing that fragment compiled. Synthetic tests cover port
selection and rejection of unsupported ports. The existing port-0 window
bounds are used as candidate validation limits for port 1, not proven port-1
resource sizes. This is data preparation only; no values were applied to the
device and no PCIe or Wi-Fi function was tested.

The earlier private link-only diagnostic hardcodes the storage port's MMIO,
reset and clock-request handling, and consumes the port-0 properties. It is
not a port-1 test by changing only the extracted table. A separate Wi-Fi
diagnostic would also need independently validated port-1 resources, reset,
clock-request and WLAN power sequencing, plus explicit DMA-disabled safeguards
and teardown; upstream S8003 uses a fixed WLAN regulator and sequences endpoint
power. The correct J71s behavior is not established and no such port-1
hardware experiment has been run.

After the extension, a default-port extraction from the same private J71s ADT
was byte-identical to the previously saved port-0 fragment. This checks that
the new option preserved this input's prior output, not every possible ADT.
The extractor can now use either the unified `orchard` ADT parser or the older
`orchard_cli` parser; both produced the same private port-1 fragment for this
input. Other device trees and the complete current upstream workflow were not
tested by that comparison.

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
