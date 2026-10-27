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
driver checks for an attached IOMMU domain but does not request DMA buffers,
submit DMA, or instantiate a PCIe host or physical endpoint. Stream 0 is a
test choice, not evidence of the storage endpoint's stream ID. The model and
isolation-checked tree and driver have not been booted; a hang may require DFU.
`prepare-software-consumer.sh` adds the driver only to the pinned disposable
kernel checkout, and `build-software-consumer-dtb.sh` rejects other boards,
existing conflicting nodes and additional IOMMU consumers.
The test kernel and image have compiled and passed component-hash checks but
have not been physically booted. `software-consumer-probe.sh` reads binding,
IOMMU group and kernel-log information after a test without submitting DMA.
`assemble-test-image.py --software-consumer` reconstructs the exact test image.
