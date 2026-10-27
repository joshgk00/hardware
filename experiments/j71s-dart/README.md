# Experimental older Apple DART stream fix

At Hoolock kernel revision `6831bc701a6ce059e71e5aaa9488c9195bea6927`,
`apple_dart_s5l8960x_write_tcr()` reads a shared register containing four
8-bit stream fields. Its read function shifts the requested field, but the
write function retains only the selected old field and ORs the new value into
the low byte. This can clear unrelated streams, retain bits intended to be
cleared, and update the wrong field for streams 1–3.

`fix-s5l-tcr-stream.patch` replaces only the selected field under the DART
spinlock and rejects an out-of-range stream or value. `test-tcr.py` extracts the actual patched C
function and executes it with a mocked register; it checks enabling and
disabling each stream, preservation of other fields, locking around register
access, and no writes for invalid
arguments. It requires a host C compiler and a separately patched kernel tree.
It also runs simultaneous mocked updates from four threads using a real host
mutex to exercise the shared-register read/modify/write path; this is not an
on-device concurrency or DMA test.
`prepare-dart.sh` applies the fix to a disposable checkout at the pinned
revision only after checking the source and patch hashes, runs the mock test
on a staged copy, and checks the resulting hash. It refuses reapplication and
does not create a device-tree node or access hardware.

The J71s Apple tree identifies a 4 KiB-page S8000 PCIe DART; the kernel's
older DART variant also uses 4 KiB pages. This similarity does not establish
that the driver works on S8000. The corrected code ran during an isolated DART
reset on one physical J71s, but has not been tested with active stream
translation or DMA. The patch itself does not enable a device tree node or establish why another
device hung during DART probe. Do not use it to access internal storage until
the controller, DMA and recovery path have been separately validated.

The J71s kernel uses 16 KiB CPU pages. In the pinned kernel, DART domain
creation rejects a DART page size larger than `PAGE_SIZE`, not a smaller one;
the IOMMU page allocator documents that sub-page allocations return a full
CPU page. This supports the feasibility of 4 KiB DART tables on this build,
but is a source-code observation, not a successful translation or DMA test.

`build-dart0-test-dtb.sh` prepares a separate DART0-only probe tree. It checks
the model, register range, IRQ, and hypothesized PCIe power domain and refuses
a base containing the PCIe host or any IOMMU consumer. A [J81 investigation](https://github.com/mattonik/ipad-nixos/blob/b94d42f78e04c5465e290340a5b6879bbc5956b6/research/t7000-pcie-hardware-findings.md)
found that its DART needed an explicit PCIe power domain to avoid a probe hang;
this supports a hypothesis, not a guarantee for J71s. Booting the test tree
powers PCIe and causes the driver to reset DART registers; it may hang and
require DFU recovery. It adds no PCIe host or NVMe device and is not a storage
access or installation test.
The current battery/SPI diagnostic reports no DART0 platform device; the
`dart0-probe.sh` read-only script records the device binding and kernel log
after a future test. The DART-only tree built and rejected the wrong board
and an existing output file. A kernel containing the stream fix also built.
`assemble-test-image.py` reconstructs that exact local test image from the
previously verified battery image and its manifest plus the DART tree and
kernel. It checks the hashes and ranges of all components, checks the final
image hash, and refuses to overwrite a file. These exact digests describe one
experimental build and are not a general installer or compatibility claim.
`add-reset-markers.py` optionally adds logs immediately before and after the
DART0 reset in a corrected source tree. They may help identify where a boot
hang occurred if the framebuffer log is visible. The markers do not change the
reset sequence. `assemble-test-image.py --reset-markers` validates the separate
marker image and refuses the non-marker kernel when this option is selected.

On one J71s physical RAM boot, the marker image logged both the start and
successful return of DART0 reset, bound `apple-dart` to `601008000.iommu`,
and registered `apple-dart.601008000.iommu` with 4 KiB pages and four streams.
USB serial and the battery gauge remained available. No PCIe host or NVMe
block device appeared. This confirms only isolated initialization; no IOMMU
consumer, translation, DMA, PCIe link or internal storage was tested.

`software-consumer.c` and `j71s-dart-consumer-test.dtso` prepare the next
experimental step: a software-only platform device attached to DART0 stream 0.
Its platform DMA configuration may allocate page tables and write DART TCR,
TTBR and TLB-invalidate registers before the diagnostic driver's probe. The
driver checks for an attached DMA-API IOMMU domain but does not request DMA buffers,
submit DMA, or instantiate a PCIe host or physical endpoint. Stream 0 is a
test choice, not evidence of the storage endpoint's stream ID. The model and
isolation-checked tree and driver have not been booted; a hang may require DFU.
`prepare-software-consumer.sh` adds the driver only to the pinned disposable
kernel checkout, and `build-software-consumer-dtb.sh` rejects other boards,
existing conflicting nodes and additional IOMMU consumers.
The test kernel and image have compiled and passed component-hash checks but
were initially untested on hardware. `software-consumer-probe.sh` reads binding,
IOMMU group and kernel-log information after a test without submitting DMA.
`assemble-test-image.py --software-consumer` reconstructs the exact test image.
`test-software-consumer.py` exercises the probe with synthetic model and domain
states: missing, blocked and identity domains are rejected; a DMA domain is
accepted. It does not simulate the kernel's pre-probe IOMMU attachment.

On one J71s boot, the software consumer joined IOMMU group 0 and its probe
reported a DMA domain. However, the DART driver also reported that its busy
bit did not clear after an invalidate command for stream 0. The pinned
driver's `apple_dart_setup_translation()` ignores the invalidate return value,
so domain registration does not establish a successful translation setup. No
physical endpoint or DMA transfer was tested. The gauge initially returned
I/O errors, then recovered on a later reading. The timeout cause is unresolved;
do not use this result to claim working DMA or storage.
Afterward, Linux's read-only power-domain summary showed `pcie` on and
`pcie_aux`, `pcie_ref`, and all four PCIe link domains off. This is a snapshot
of Linux's domain state, not proof of physical clock state or evidence that
turning on another domain will resolve the timeout.
Three later read-only samples of the command-status register, one second apart,
each showed bit 3 set. That is the bit the current older-DART driver treats as
busy, so it did not appear to clear within that sampling window. The bit's
meaning on S8000 is not independently established. `busy-observe.sh` checks
the J71s model and bound driver before repeating this read; it writes no
registers and sends no commands.
The stream-0 control register also had the driver's translation-enable bit
set, but a later full-value check showed the entire register read as all ones.
That does not establish that the requested control bit was retained.

A further read-only sample reported the command register value was at least
`0x1000` and bit 12 was set while bit 3 remained set. The meaning of bit 12
and the reason for the stuck busy bit are not established. The observer now
reports these fields without exposing the full register value.

A subsequent isolated RAM boot tested an experimental kernel that requested
invalidation of all four streams for the software-only stream-0 consumer.
The diagnostic logged that the experimental path ran, but the same busy-bit
timeout occurred. Three later read-only samples again showed bit 3 set, the
command register value at least `0x1000`, and bit 12 set. The test did not
instantiate a PCIe host, submit DMA, or access storage. Thus requesting all
four streams alone did not resolve the timeout; the cause remains unknown.

After the all-stream test, read-only checks found that five DART0 offsets
(command, stream control and three configuration offsets) all returned
`0xffffffff`. This may mean the block is unavailable or not responding; the
cause and when the all-ones state began are unknown. It also means the earlier
busy-bit and translation-enable observations cannot independently establish
actual controller state. The driver can report reset completion despite these
reads; binding and reset return therefore do not establish working hardware.
A future test must sample before the first command as well as afterward and
should investigate power and availability without attaching a physical DMA
consumer.

`pcie-pmgr-observe.sh` reads the PCIe power-state registers without writing
anything, after checking the device-tree model. On the all-stream boot, the
main PCIe gate reported actual and target state 15 (active), with automatic
power management enabled and neither reset nor device-disable asserted. The
AUX, reference and link gates reported actual and target state 0. The register
values were not all ones. This is a momentary PMGR report, not proof that all
clocks or the DART are accessible, nor evidence that enabling another gate is
safe or sufficient.

A further RAM boot instrumented the same three DART register reads immediately
before and after the driver's reset. All three read as `0xffffffff` at both
points, before the software consumer's invalidate command. Thus the all-ones
response was already present before that reset and command in this boot. The
main PCIe PMGR gate again reported active afterward, while AUX, reference and
link gates reported off. The evidence points to an availability or sequencing
problem, but does not distinguish an inaccessible hardware block from another
cause, and does not establish when before the driver's probe the state arose.
No PCIe endpoint or DMA was enabled.

`aux-power-holder.c` and `j71s-aux-holder.dtso` describe a separate,
untested J71s experiment. The overlay gives a software-only platform device the
PCIe AUX power domain; the tiny platform driver stays bound without requesting
DMA or accessing a controller. Platform-device probe attaches and powers its
single domain. The experiment is intended to compare the DART register reads
before and after AUX becomes active, using `pcie-pmgr-observe.sh` and
`busy-observe.sh`. It does not add the PCIe host or storage endpoint. Turning
on the power domain is a hardware change and may hang or require DFU recovery;
its safety and whether it affects DART availability are not established.

An isolated test kernel incorporating the holder and a separate device tree
have compiled. The exact local image and component hashes were checked, and the
test tree retains the previously checked software-only consumer; no physical
boot of this AUX experiment has yet occurred. A bound holder alone does not
prove the gate reached its requested hardware state: check the power-state
register separately.
`aux-power-probe.sh` combines the read-only checks for holder binding, AUX
actual/target state, five DART register all-ones comparisons, and relevant boot
messages. On the prior baseline boot it correctly reported no holder, AUX off,
and all five DART reads as all ones. That baseline result does not test AUX-on
behavior.
`prepare-aux-holder.sh` adds the holder to a disposable checkout at the pinned
kernel revision after verifying the existing software-consumer source, IOMMU
Makefile and holder source hashes. It refuses reapplication and changes no
device tree or hardware. A prepared copy matched the source and Makefile used
for the compiled experiment; this check does not validate the rest of the
kernel checkout or the device tree.

On one physical J71s RAM boot, the AUX holder bound and PMGR reported AUX
actual/target state 15, while the main PCIe domain also reported active and
reference/link domains remained off. All five observed DART registers still
read as `0xffffffff` after AUX became active. DART probe and its invalidate
attempt occurred before the AUX holder bound, so this shows AUX activation
alone did not make the registers respond afterward; it does not test powering
AUX before DART probe or together with the reference domain. No physical DMA,
PCIe host or storage endpoint was enabled. Battery and system remained
responsive, but enabling AUX increased the reported discharge current.
After collecting the result, the test holder was unbound. AUX returned to
actual/target state 0 and reported discharge current fell from approximately
363 mA to 256 mA. These are individual gauge samples, not power measurements
or proof of battery accuracy.

`j71s-ref-holder.dtso` is a second untested overlay for the auxiliary test
image. It binds another instance of the same software-only holder driver to the
PCIe reference power domain. Its driver log retains the AUX test name; use the
platform-device name and PMGR register readings to distinguish the two. A
separate RAM image with both overlays was assembled and its domain phandles,
register offsets, kernel and image hashes checked. It has not been booted.
As with the AUX-only test, DART probe happens before these holders bind; this
experiment checks register access after both domains are requested, not the
initial power-up ordering. Both domains may increase battery drain and can be
released after observation. No PCIe host or storage endpoint is enabled.
The observer also reports the reference holder and reference gate; on the
AUX test after cleanup both gate targets and actual states were zero. Boot
messages are historical, so current binding is reported separately.
