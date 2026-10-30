# Experimental older Apple DART stream fix

For the current hardware state and next action, see [STATUS.md](STATUS.md).

**Maintainer feedback, 2026-10-29:** the original `fix-s5l-tcr-stream.patch`
and its test are historical. Its use of `dart->lock` can deadlock when a
caller already holds that lock. Orchard accepted the race report and landed a
separate TCR lock in [hardware commit f82f35a](https://github.com/OrchardLinux/hardware/commit/f82f35a396d314bd815a2f44e01727993e30cc21),
closing [linux PR 1](https://github.com/OrchardLinux/linux/pull/1). The
maintainer tested the upstream implementation on iPad 6; that does not prove
J71s DMA. `j71s-dart-distinct-tcr-lock.patch` updates our older experimental
kernel after the original patch to use a dedicated lock. The separate test
`test-tcr-distinct-lock.py` checks the real function when the general lock is
already held, concurrent updates, and bounds. The separately extracted J71b
storage-driver tree already had the field correction but lacked locking;
`j71b-dart-distinct-tcr-lock.patch` records its corresponding update. Do not use
the original patch alone as the basis for new experiments.

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
`prepare-dart.sh` applies the historical field correction and then the separate
TCR-lock follow-up to a disposable checkout at the pinned revision. It verifies
the source and both patch hashes, runs the corresponding mock tests on a staged
copy, and checks the resulting hash before updating the checkout. It refuses reapplication and
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

On one physical J71s boot with the combined overlays, both holders bound.
AUX reported actual/target 15; reference reported target 15, actual 4, and
automatic power management enabled. The pinned PMGR driver names state 4 as
clock-gated, so binding the reference holder did not establish that its clock
was running during the observation. Five DART registers still read all ones.
The DART probe preceded both holder bindings, so this test does not establish
whether activating the reference clock before probe would help. No physical
DMA or storage endpoint was enabled. Afterward both holders were unbound; both
gates reported actual/target 0 and the gauge's sampled discharge current fell
from approximately 444 mA to 260 mA. Gauge accuracy remains unverified.

`j71s-ref-min-active.dtso` prepares another untested RAM experiment: it sets
the reference power domain's `apple,min-state` to 15. The pinned PMGR binding
describes this as the minimum auto-power state (15 means on), and the driver
programs that field during domain probe. The overlay is layered on the AUX
and reference holder test, and the assembled image, DTB, model, domain offset
and absence of a PCIe host were checked. This may keep the reference domain
active and increase battery drain until reboot; actual behavior and whether it
helps DART access are unknown. The holders bind after DART probe, so the test
still cannot establish whether a different initial probe ordering would help.
It changes hardware power management, may hang, and may require DFU recovery.
No storage endpoint or physical DMA is enabled.
The power-state observer reports each gate's minimum auto-PM state. Before the
minimum-state experiment, the reference gate's minimum field read 0. This is a
single read-only baseline, not evidence the later setting will take effect.

On one physical J71s RAM boot with the minimum-state overlay, PMGR reported
reference actual/target/minimum 15 with auto-PM enabled, and AUX actual/target
15. All five observed DART registers still read `0xffffffff` after both
holders bound. DART probe occurred earlier, so this does not test either gate
being active before the initial reset. After both holders were unbound, AUX
and reference actual/target states returned to 0; the reference minimum field
remained 15 while auto-PM was disabled. The reported battery capacity was 62%
after cleanup, with sampled discharge current about 262 mA. No PCIe host,
physical DMA or storage endpoint was enabled.

`j71s-dart-early-power.dtso` and `j71s-dart-early-power.patch` prepare a
separate, untested ordering experiment on the existing availability-test
kernel: the J71s DART driver attaches three power domains before its first
DART register read and logs their reported actual states. The overlay requests
an active reference minimum state. The code is specific to the experimental
J71s tree and opts in through a test-only property; it is not a general driver
fix. The kernel compiled and the device tree and assembled RAM image were
checked. This requests hardware power, may hang, and can increase battery
consumption while the diagnostic runs. It does not enable a PCIe host,
physical DMA or storage endpoint. A restart may be needed to release power.

On a physical J71s early-power RAM boot, the diagnostic logged main PCIe,
AUX and reference actual state 15 before its first DART read. The command,
stream-control and configuration registers all read `0xffffffff` both before
and after reset; invalidate again timed out. Thus, these three domains being
reported active before probe did not by itself make DART0 respond in this
boot. This does not rule out other dependencies or a different initialization
sequence. The software-only consumer joined an IOMMU group; no physical DMA,
PCIe host or storage endpoint was enabled. The battery initially returned I/O
errors but a later sample reported 61% and approximately 443 mA discharge
with the test power domains active. Restarting is needed to release these
probe-owned domains; the gauge's accuracy is unverified.

`j71s-dart-early-link.dtso` and `j71s-dart-early-link.patch` build on the
three-domain experiment with a fourth domain: PCIe link 0. The diagnostic
requests it before DART probe and logs its power state, with an active minimum
state. The kernel compiled, the new tree and image hashes were checked, and
the patch was checked against the preceding diagnostic source. This has not
been physically booted. It powers a domain associated with the storage link,
but adds no PCIe host, storage endpoint or physical DMA consumer. Turning on
this additional domain can affect hardware and battery use, may hang, and may
require a reboot or DFU recovery.

On one J71s RAM boot with the four-domain link-0 experiment, PMGR reported main
PCIe, AUX, reference and link 0 actual state 15 before the first DART read.
The command, stream-control and configuration registers still read all ones
before and after reset, and invalidation timed out. Thus these four requested
power domains, in this ordering, were not sufficient to make DART0 respond.
The other link domains remained off; this is not a test of them or of the
complete controller initialization sequence. No PCIe host, physical DMA or
storage endpoint was enabled. The gauge initially reported I/O errors, then
reported 60% and approximately 396 mA discharge after brightness reduction.
The test domains remain probe-owned until restart.

On the four-domain boot, three selected 32-bit registers in the PCIe shared
controller window returned values other than all ones in a read-only test.
The first read returned zero; the other two were nonzero. DART0 registers
still returned all ones. These observations show that some shared-window
reads responded under this configuration, not that PCIe or storage works.
The selected shared registers were not written, no host was registered, and
no physical DMA or storage command was issued.

A later read-only check of one port-0 register in the PCIe/NVMe-MMU-overlapping
window returned `0xffffffff`, while the previously tested shared-controller
window had returned other values. Main PCIe, AUX, reference and link-0 PMGR
states were reported active immediately before this check. The meaning of the
all-ones response remains unknown; this is not a PCIe link, DMA or storage
access test. The port register was not written.

A later J71s RAM-only shared-controller diagnostic requested the same four
PCIe power domains, then briefly changed a small guarded subset of controller
control bits. During the sequence, a port-0 register and a DART0 register
both returned values other than all ones; both had returned all ones during the
previous four-domain power-only test. The three saved shared-control registers
read back as restored afterward, and a later observation found the four power
domains off. This is evidence that controller setup can affect register
accessibility; it does not prove that all hardware effects were reversed, that
the PCIe link or address translation works, or that storage is accessible. The
test enabled no PCIe host, physical DMA or storage endpoint and issued no
storage commands.

In a later single-CPU RAM-to-RAM boot, a guarded follow-up repeated the shared
control sequence and confirmed that DART command, TCR, error and first TTBR
samples were not all ones. With no physical DMA or PCIe host enabled, an
all-four-stream DART invalidate returned success with its busy bit clear in a
bounded poll. The same command had timed out during an earlier inaccessible
state. The saved shared-control registers read back as restored. This verifies only that the tested busy-bit poll returned success. Later
experiments found that the command register could retain the written value.
This is not proof the invalidation executed, DMA translation works, or hardware
side effects were completely reversed. The test image was reached by a successful single-CPU kexec
handoff; this does not establish general-purpose warm-boot support.

A follow-up single-CPU RAM-to-RAM test retained the experimental shared
controller settings while the actual DART driver initialized. Its register
samples remained accessible before and after driver reset. The existing
software-only consumer entered IOMMU group 0, the driver's all-four-stream
invalidation busy-bit poll returned without the earlier timeout, and the consumer reported
a DMA domain. The test did not allocate or submit physical DMA, register a
PCIe host, or access internal storage. The experimental cleanup is intended
for probe failure and shutdown; hardware shutdown restoration and actual
address translation remain to be verified.

A later RAM-only software-consumer test allocated and mapped one page with the
DMA API, checked both ends with `iommu_iova_to_phys`, unmapped it, and verified
the lookup disappeared. On the J71s, all three checks passed and the DART
invalidation log showed no timeout. These lookups examine software page
tables; no hardware DMA transaction, PCIe host or storage command was issued.
The result therefore does not establish hardware translation or storage.

`software-map-consumer.c` preserves the experimental page-mapping probe; it
is not part of a production kernel configuration. `test-software-map.py`
extracts the actual probe and checks a host DMA/IOMMU mock for success,
allocation and mapping failure, first/last lookup mismatches, unmap, and page
cleanup. Run `python3 experiments/j71s-dart/test-software-map.py` from the
repository root. The mock checks software control flow only; the physical
observation above checks the software page tables, not hardware DMA.

After DFU recovery, the software-only mapping result repeated. With the test
DART bound and the four power domains active, separately guarded read-only
checks of common-window offsets `0x2c` and `0x12c` and port offset `0x088`
returned values other than all ones. Common `0x12c` read as zero; bit 0 was
clear in each sample. Candidate field names from S8003 are not established
semantics on S8000. A separate streaming check logged a marker immediately
before reading port offset `0x804` and then stopped responding and timed out.
The exact cause is unconfirmed, but this isolates the observed stall to that
access or its immediate execution. Avoid repeated reads of that candidate.
The checks issued no register writes, hardware DMA or storage commands.

A guarded experiment added a candidate port-power bit from a related S8003
sequence and polled common offset `0x12c` for readiness before proceeding.
On J71s, both a 1 ms poll and a later 250 ms poll timed out with bit 0 clear
and without all-ones reads. The saved shared controls read back as restored
in both tests. Neither test accessed port offset `0x804`; both stopped before
DART invalidation or PCIe host registration. The longer wait rules out a
simple delay up to 250 ms for this partial sequence, but other prerequisites
and the S8000 register semantics remain unknown. No physical DMA or storage
access was attempted.

A further guarded test omitted the additional bit 8 from the earlier control
write and checked common `0x2c` bit 4 before enabling the next candidate
control. That prerequisite was set, but the `0x12c` bit-0 check still timed
out after 250 ms without an all-ones read. Saved controls read back as
restored. This test narrows the behavior of the partial sequence; it does not
establish the complete S8000 initialization path. It stopped before DART
invalidation, host registration, physical DMA or storage access.

`j71s-port-sequence-experiment.patch` preserves the exact `apple-dart.c`
changes used for the last candidate-ordering test, as a single patch against
Hoolock kernel `6831bc701a6ce059e71e5aaa9488c9195bea6927`. It is experimental
bring-up code, not a production driver: in addition to the opt-in register
experiment, it changes the J71s DART invalidate behavior even outside the
opt-in probe. It must only be used in an isolated recovery-capable RAM test;
it does not enable or validate a storage installation. The relevant opt-in
properties and power-domain overlays are preserved in `j71s-dart-early-power.dtso`,
`j71s-dart-early-link.dtso`, and `j71s-shared-bits-test.dtso`; they build on
`j71s-dart0-test.dtso` and the required J71s power-domain definitions. These
files preserve the diagnostic inputs rather than a complete boot image.

For an offline control-flow check, apply the patch to a disposable copy of the
pinned kernel and run `python3 experiments/j71s-dart/test-port-sequence.py
/path/to/patched/drivers/iommu/apple-dart.c`. The test extracts the actual
opt-in block and exercises a host MMIO mock, including prerequisite failures,
write order, and restoration. It does not simulate timing, prove hardware
safety, or verify physical DMA. A byte comparison confirmed that applying the
saved patch to the pinned `apple-dart.c` reproduces the source file used for
the physical candidate-ordering test.

The tested device's captured tree also contains common and PHY PCIe tuning
properties. An offline shape check found 34 common and 41 PHY records, all
with aligned 32-bit accesses fitting the sizes of candidate register windows;
the PHY window mapping remains unverified. One common-table entry targets the
same offset `0x100` as the diagnostic but does not mask either tested bit 0
or bit 8. The diagnostic did not apply these tables. Their presence is a
configuration difference to investigate, not evidence that replaying them is
safe or sufficient to establish PCIe or storage.

A follow-up boot reported both bits from the same already-existing common
`0x2c` sample during the candidate ordering test. Bit 4 was set and bit 0
was clear; the `0x12c` port-status bit again remained clear for 250 ms, and
the saved controls read back as restored. This adds no hardware access to
the prior diagnostic and narrows the observed state; it does not establish
what is required to set the global bit or bring up the link.

On a separate DART-bound boot, a guarded read of common controller offset
`0x04` returned 1, with bit 4 clear. This read completed with the four tested
power domains active and no PCIe devices present. It was read-only; no global
initialization write or tuning operation was attempted. The meaning and
hardware side effects of any future write remain to be established.

An isolated J71s RAM boot tested a candidate global initialization operation.
After checking the four power domains and a common `0x04` baseline of 1, the
test set bit 4 and observed common `0x2c` bit 0 set in its bounded poll.
It wrote back the saved control value, which read back as matching. The test
then aborted before DART initialization, PCIe host registration, tuning-table
application, physical DMA or storage access. This demonstrates a global
status transition on one device, not a working PCIe link or proof that every
hardware side effect was reversed.

A later guarded RAM boot combined the candidate global initialization with
the previous port sequence. Common `0x2c` bit 0 became set, and the subsequent
common `0x12c` bit-0 port-status poll also succeeded without all-ones reads.
The saved global and port controls read back as restored. Unlike the earlier
port-only attempts, this test observed the candidate ready status. It stopped
before DART-register accesses, host registration, tuning-table application,
physical DMA or storage access. The observation does not establish a trained
link, an endpoint, or reversal of every hardware side effect.

A follow-up boot repeated both ready-status observations and then sampled
port-window offset `0x210`. The read completed but still returned all ones;
the saved global and port controls read back as restored. This isolates a
remaining accessibility issue after the tested partial initialization. No
DART-register access, host registration or storage command was attempted.

In a follow-up RAM boot, the same global and port-ready checks succeeded. The
experiment then set common `0x124` bit 0 and waited 100 microseconds before
reading port offset `0x210`; this time the read returned zero rather than all
ones. Both sets of saved controls read back as restored. This is evidence of
a register-accessibility change in one physical test, not a trained link,
endpoint, DMA or storage result. No DART-register access, PCIe host or storage
command was attempted.

With the same guarded global, port-ready and reference-clock sequence, an
isolated read of candidate port link-status offset `0x208` completed and
returned zero, with bit 3 clear. Saved controls read back as restored. Related
hardware uses this offset for link status, but the S8000 field meaning is not
established, and the test did not start link training or access storage.

Separate read-only observations after the diagnostic restored its controls
found the candidate storage reset GPIO 160 in mode 0, peripheral selector 0,
with input enabled; candidate clock-request GPIO 164 was in mode 0, peripheral
selector 1, with input enabled. Under the Linux Apple GPIO driver's direction
logic, mode 0 is treated as input. These samples do not establish reset
polarity or its state during the enabled-port sequence; neither pin was changed.

A follow-up RAM diagnostic sampled the same candidate GPIOs while the tested
global, port-ready and reference-clock controls were active. Reset pin 160
again reported mode 0, peripheral selector 0 and input enabled; clock-request
pin 164 reported mode 0, peripheral selector 1 and input enabled. The values
matched the post-restoration observations. No GPIO was written and link
training was not started, so reset polarity and the necessary drive sequence
remain unverified.

The related J71b Linux driver defines its PCIe PERST GPIO as active low and
asserts it before port initialization, then deasserts it after reference-clock
setup. That is useful comparative evidence but does not by itself establish
the J71s platform-function encoding, pin polarity, timing units or complete
S8000 initialization order. No J71s reset GPIO drive has been attempted.

A guarded RAM-only experiment tested the candidate active-low reset GPIO 160
under the successful global and port-control sequence. After checking its
input/peripheral baseline, the diagnostic drove the pin low then high; the
high output configuration read back, and its original mode and peripheral
bits read back as restored. The candidate port link-status sample remained
zero. This establishes GPIO register behavior, not electrical reset polarity,
endpoint behavior or a trained link. It issued no storage commands or physical
DMA and did not register a PCIe host.

A bounded diagnostic combined the tested initialization and candidate GPIO
reset pulse with a candidate link-training operation: it set port `0x80`
bit 0, then polled port `0x208` bit 3 for 250 ms. The poll timed out without
all-ones reads; the training control, GPIO mode/peripheral bits and saved
shared controls read back as restored. The iPad remained responsive. This
partial sequence did not apply PCIe tuning tables or register a PCIe host,
and it issued no storage commands or physical DMA. The S8000 status semantics
and reversal of all hardware effects remain unverified.

After the tested global, port-ready and reference-clock sequence, an isolated
read of the first captured PHY-tuning offset in the candidate PHY window
completed but returned all ones. The nearby port control sample remained
readable and the saved controls read back as restored. This result does not
prove the candidate PHY mapping is wrong or that all of its registers behave
alike. The test performed no PHY writes, link training or storage access.

A guarded follow-up observed common `0x38` at zero, wrote 1 and sampled the
same candidate PHY register. It returned a nonzero, non-all-ones value, unlike
the previous all-ones observation. The test wrote `0x38` back to zero, with
matching readback, and restored the previously saved controls. This shows a
change in accessibility for one PHY register in one sequence, not proof that
all PHY tuning is safe, the link is trained or all effects were reversed. No
PHY tuning writes, host registration or storage access occurred.

A private, isolated diagnostic applied the first captured PHY tuning record
under the tested global and PHY-control sequence. The accessible register's
value changed, the written value read back as matching, and the saved register
and controls read back as restored. The iPad remained responsive. This checks
one record on one boot; it does not establish safety of the full table, a
trained link or reversal of every side effect. It performed no link training,
physical DMA or storage access. Device-specific tuning values are not included.

A private guarded RAM diagnostic applied all 41 captured PHY tuning records
under the tested initialization sequence. Each write read back as expected;
reverse-order restoration reported zero readback errors, and the saved PHY
gate and other controls also read back as restored. The iPad remained
responsive. This is one register-readback test, not proof of a trained link,
storage or reversal of every side effect. It did not start link training,
register a host, perform physical DMA or access storage. Device-specific tuning
values are not included here.

A follow-up diagnostic applied all 41 private PHY records, then performed the
bounded candidate reset and link-training sequence while they remained active.
All tuning writes read back, but candidate port `0x208` bit 3 remained clear
for 250 ms. The training, GPIO and shared controls read back as restored, and
PHY rollback reported zero readback errors. The device remained responsive.
This partial test did not apply common-controller tuning, register a PCIe host,
perform physical DMA or issue storage commands; it does not establish the
S8000 status semantics or reversal of all hardware effects.

A private guarded RAM diagnostic applied all 34 captured common-controller
PCIe tuning records. Each write read back as expected; reverse-order rollback
reported zero readback errors, and the PHY gate and other saved controls read
back as restored. The iPad remained responsive. This is one register-readback
test, not proof of safe link operation or reversal of every side effect. It
performed no link training, host registration, physical DMA or storage access.
Device-specific tuning values are not included here.

A dual-tuned diagnostic applied all 41 PHY and 34 common-controller records,
then attempted the bounded candidate reset and training sequence. Both tables
passed write-readback, but candidate port `0x208` bit 3 remained clear for
250 ms. Both tables reported zero rollback readback errors, and the tested
training, GPIO and shared controls read back as restored. The iPad remained
responsive. Per-port tuning was not applied, and no PCIe host, physical DMA or
storage command was used. This does not establish the precise S8000 status
semantics or reversal of every hardware effect.

A private guarded diagnostic applied all six captured per-port configuration
records to the candidate port window. Each write read back as expected and
reverse-order rollback reported zero readback errors; the saved controls also
read back as restored. The iPad remained responsive. The separate root-complex
table was not tested, and no link training, host registration, physical DMA or
storage access occurred. This does not prove a working link or reversal of all
hardware effects; device-specific tuning values are not included.

A further diagnostic applied all 41 PHY, 34 common and six port records,
then ran the bounded candidate reset and link-training sequence. All records
passed write-readback, but candidate port `0x208` bit 3 stayed clear for
250 ms. All three table rollbacks reported zero errors and the tested controls
read back as restored. The iPad remained responsive. The root-complex table was
not applied, and no host, physical DMA or storage command was used. This does
not establish the exact S8000 link semantics or reversal of every side effect.

An isolated read of offset zero in the candidate root configuration window
completed after the tested global, port-ready and reference-clock steps and
returned a nonzero, non-all-ones value. Saved controls read back as restored,
and the iPad remained responsive. This demonstrates a responding candidate
root-window read, not endpoint enumeration, link training or storage. No root
tuning, host registration, physical DMA or storage command occurred.

A read-only follow-up sampled both candidate root-tuning offsets `0x98` and
`0x154` after the root-window guard. Both reads completed without all-ones
values; the first returned zero and the second a nonzero value. Saved controls
read back as restored and the iPad remained responsive. No root tuning writes,
link training, host registration, physical DMA or storage access occurred.
Related drivers enable certain configuration writes before tuning; whether
that is required and safe on J71s remains unverified.

A guarded root-tuning diagnostic found the first captured record already
matched its register. With the candidate configuration write-enable bit set,
the second record wrote and read back as expected; its saved value, the enable
control and shared controls read back as restored. The iPad remained
responsive. This checks one record under one sequence, not a trained link,
storage or reversal of every side effect. No link training, PCIe host,
physical DMA or storage command was used; device-specific values remain private.

A follow-up diagnostic added the previously checked root tuning to the three
other tables and attempted the bounded candidate reset and training sequence.
All tuning readbacks passed, but candidate port `0x208` bit 3 stayed clear for
250 ms. Root target and write-enable, the three tables, GPIO and shared
controls reported matching restoration readbacks; the iPad remained responsive.
No PCIe host, physical DMA or storage command was used. This does not establish
S8000 link-status semantics or reversal of every side effect.

An additional bounded training diagnostic sampled candidate state bits and the
high byte of port `0x208`, and bits 0 and 6 of port `0x88`. All were zero after
the 250 ms poll timed out. The reads completed, rollback readbacks passed, and
the iPad remained responsive. The fields' S8000 meanings remain unverified;
no PCIe host, physical DMA or storage command was used.

After the tested global and port-ready sequence, a read of candidate common
link-rate offset `0x4020` returned zero. A guarded follow-up wrote 3 only from
that zero baseline; the full register readback did not equal 3. Restoring the
saved zero and shared controls read back as matching. The iPad remained
responsive. This mismatch may reflect register semantics, prerequisites or
ordering; it does not establish that the write had no effect or that all side
effects were reversed. No link training, host, physical DMA or storage command
was used in these tests.

Repeating the guarded `0x4020` write after the checked PHY, common, port and
root tuning sequences again started from zero and immediately read back zero
after writing 3. Saved controls and tuning rollbacks read back as restored,
and the iPad remained responsive. This does not determine whether the register
is write-only, self-clearing, gated or otherwise behaves differently; write
side effects cannot be excluded. No reset pulse, link training, host, physical
DMA or storage command was used.

During another bounded training attempt, port `0x80` control bit 0 read as set,
but the low byte of port `0x208` was zero, including the bit named link-up in
a different Apple PCIe controller driver. Candidate state and high-byte fields
and port `0x88` bits 0 and 6 were also zero. Rollback readbacks passed and the
iPad remained responsive. The field meanings on S8000 remain unverified; no
PCIe host, physical DMA or storage command was used.

Static comparison identified a candidate post-ready operation that clears
common `0x100` bit 8. In the existing test that bit was set. A guarded
follow-up cleared it after port-ready and confirmed it stayed clear through
tuning, but the candidate training poll still timed out with the status low
byte zero. Tuning and saved controls reported successful restoration readbacks;
the iPad remained responsive. The inferred operation alone was insufficient
in this test. No PCIe host, physical DMA or storage command was used.

A further bounded training test combined the post-ready bit clear with a
zero-baseline-guarded write of 3 to candidate common `0x4020` immediately
before training. The immediate readback was zero; the poll timed out with the
status low byte zero and training-control bit 0 set. A subsequent zero write
read back as zero, and saved controls and tuning reported restoration
readbacks. The iPad remained responsive. The command's effects and complete
startup ordering remain unverified. No PCIe host, physical DMA or storage
command was used.

A storage-mode comparison found two candidate common controls at the baselines
inferred from the matching device's properties. Guarded isolated writes of the
candidate values read back successfully and their saved values read back after
restoration. A combined test applied both settings with the post-ready clear,
tuning, reset, rate-command and bounded training sequence. The training poll
still timed out with the status low byte zero. Mode and other tested controls
and tuning reported restoration readbacks; the iPad remained responsive.
These partial tests do not establish a link or prove reversal of all effects.
No PCIe host, physical DMA or storage command was used.

Under the combined storage-mode and tuning sequence, a guarded DART invalidate
poll returned with busy clear. A detailed repeat showed the command register
had the same value before and after the write. Consequently this is
inconclusive and does not demonstrate command execution or physical DMA. The
link poll still timed out; reported control and tuning restoration readbacks
passed, and the iPad remained responsive. No translation, PCIe host, DMA or
storage I/O was enabled.

A guarded repeat used a distinct single-stream command after the observed idle
baseline. The command-register readback changed, but a stricter bounded poll
with an incorrectly inferred extra condition timed out (see correction below).
This shows a changed register value, not a completed invalidation. The link
poll also timed out; tested controls and tuning reported restoration readbacks,
and the iPad remained responsive. No translation, PCIe host, physical DMA or
storage I/O was enabled.

Static investigation of the storage bridge's separate NVMe MMU activation
function points to initialization of a candidate MMU window, including
address-like fields and a control/status bit. A read-only diagnostic sampled
candidate window `0x601004000` offset `0x04` after the tested port-ready
sequence; it returned zero, saved controls read back as restored, and the
iPad remained responsive. The mapping, address-field provenance and complete
activation sequence remain unverified. No MMU write, PCIe host, physical DMA
or storage command was used.

A read-only follow-up classified candidate NVMe MMU offsets `0x08`, `0x0c`
and `0x20` as zero, and `0x10` and `0x14` as nonzero and not all ones. It did
not log the field values or write them. Saved controls read back as restored
and the iPad remained responsive. The nonzero values' meaning and provenance
are unknown; they do not establish valid Linux DMA addresses or working
storage. No MMU writes, PCIe host, physical DMA or storage commands were used.

The related [Corellium iPhone PCIe driver](https://github.com/corellium/linux-sandcastle/blob/sandcastle-5.4/drivers/pci/controller/pcie-hx.c)
sets port `0x140` bit 31 before link training, and the matching iPadOS
controller contains a helper that controls the same bit. A guarded diagnostic
set it and checked readback. The candidate link poll still timed out with
port `0x208` state and low byte zero, but port `0x88` bit 0 was set; it had
been clear in the comparable previous test without the enable write. Its
exact S8000 meaning remains unverified and this is not evidence of a trained
link. The saved port value and other tested controls and tuning read back as
restored; the iPad remained responsive. No PCIe host, MMU address write,
physical DMA or storage command was used.

With port-enable set, a corrected GPIO observation sampled the candidate
clock-request pin's data bit as 1 during reset-low and 0 after reset-high and
after training; input-enable remained set. The related driver's active-low
convention makes this consistent with a request after reset, but J71s pin
routing and electrical interpretation remain unverified. The candidate link
state remained zero, saved controls reported restoration readbacks and the
iPad remained responsive. An earlier observation of bit 9 alone measured
input-enable, not the signal level.

A further bounded poll used the related Sandcastle driver's candidate link
state range `0x11`–`0x14` for 500 ms. The observed state remained zero and the
poll timed out; the port-enable indication remained set. The candidate
clock-request GPIO data bit was low after reset release. Tested controls and
tuning reported restoration readbacks and the iPad remained responsive. The
state field's S8000 semantics remain unverified. No PCIe host, physical DMA or
storage command was used.

A guarded follow-up held the candidate storage reset low during port setup
and released it before the 500 ms state-based training poll. The candidate
state remained zero and the poll timed out. Reset mode, tested controls and
tuning reported restoration readbacks; the iPad remained responsive. This
ordering alone was insufficient in this partial sequence. Reset polarity and
reversal of hardware side effects remain unverified. No PCIe host, physical DMA
or storage command was used.

A guarded follow-up applied both candidate storage-mode writes before port
setup, with a 5 ms interval and candidate reset held low, then ran the bounded
500 ms link-state test. Both writes read back as expected, but the candidate
state remained zero and the poll timed out. Reset mode, tested controls and
tuning reported restoration readbacks; the iPad remained responsive. This
partial ordering and timing change alone was insufficient. No PCIe host,
physical DMA or storage command was used.

A private follow-up applied the 41 previously checked PHY tuning records
before storage-mode and port setup. All were accessible and passed immediate
write-readback, but the subsequent 500 ms candidate link-state poll remained at
zero and timed out. Both tuning rollbacks reported no readback errors, and the
gate and saved controls read back as restored; the iPad remained responsive.
This establishes early accessibility under one sequence, not a working link
or reversal of all effects. No PCIe host, physical DMA or storage command was
used. Device-specific tuning values remain private.

A private follow-up applied all 41 PHY and 34 common tuning records before
storage-mode and port setup, preserving the tuned bits in the overlapping port
control. All records passed immediate readback, but the 500 ms candidate link
state poll stayed at zero and timed out. Early and later tuning rollbacks
reported zero readback errors; the gate, reset and saved controls read back as
restored, and the iPad remained responsive. This verifies the tested ordering
and readbacks, not link operation or reversal of all effects. No PCIe host,
physical DMA or storage command was used; tuning values remain private.

A further guarded test cleared candidate common clock-control `0x114` bit 8
after port readiness; it was initially set and read back clear during the
test. Port enable read back as set, but the 500 ms candidate link-state poll
still timed out at zero. Tested tuning, reset and shared controls reported
restoration readbacks, and the iPad remained responsive. The runtime branch
and hardware side effects remain unverified. No PCIe host, physical DMA or
storage command was used.

A private follow-up kept the candidate PHY gate enabled through early tuning,
port setup and link training instead of closing and reopening it. The 500 ms
candidate link-state poll still timed out at zero. Tuning rollbacks reported no
readback errors, and the gate and saved controls read back as restored; the
iPad remained responsive. This was insufficient in the tested sequence and
does not prove reversal of all effects. No PCIe host, physical DMA or storage
command was used.

A bounded read-only walk of the root PCI Express capability list found a
capability whose target-link-speed field was already set to 2 before training.
The 500 ms candidate link-state poll still timed out at zero; reported tuning
and control restoration readbacks passed, and the iPad remained responsive.
This observation does not establish link operation or reversal of all effects.
No PCIe host, physical DMA or storage command was used.

A guarded follow-up set candidate common control `0x134` bit 0 after the
reference-clock delay and verified readback. The 500 ms candidate link-state
poll still timed out at zero. The control and other saved registers read back
as restored, tuning rollback reported zero errors, and the iPad remained
responsive. This step was insufficient in the tested partial sequence and
readback does not establish reversal of all hardware effects. No PCIe host,
physical DMA or storage command was used.

A follow-up issued the previously tested candidate link-rate command after the
reference-control step and before reset release. Its register read zero
immediately; the 500 ms candidate link-state poll still timed out at zero.
Reported control and tuning restoration readbacks passed, and the iPad remained
responsive. Command semantics and reversal of hardware side effects remain
unproven. No PCIe host, physical DMA or storage command was used.

An additional read of port `0x210` immediately after the candidate rate
command and before reset release returned zero, as did the later sample.
The 500 ms candidate link-state poll still timed out at zero. Tested control
and tuning restoration readbacks passed, and the iPad remained responsive.
This observation does not establish link operation or reversal of all
hardware effects. No PCIe host, physical DMA or storage command was used.

Correction: the original ARM64 poll exits when the command value is below
`0x1000` **or** bit 3 is clear. The `ccmp` fallback sets the zero flag when
the threshold comparison is false. Earlier statements that the driver requires
both a value at least `0x1000` and a clear busy bit were incorrect; the
stricter experimental timeout does not show that the original poll timed out.
Neither poll result alone proves hardware invalidation or DMA.

A standalone ARM64 user-space check, `ccmp-check.S`, executes the relevant
comparison and conditional comparison for values `0`, `8`, `0x1000`, and
`0x1008`. On the connected iPad it exited with bit mask `7`, meaning the first
three cases take the exit branch and the fourth does not. This confirms the
instruction-level interpretation on that CPU; it does not validate hardware
register semantics or an actual DART invalidation. The program performs no
MMIO and makes only the process-exit system call.

`j71s-all-link-domains.dtso` prepares a RAM-only experiment requesting the
PCIe parent, auxiliary, reference, and all four link domains through the
existing Linux power-domain driver. It preserves the existing LINK0 minimum state without setting minimums for
the other three links. The generic m1n1 `pmgr_adt_devices_set_mode` helper iterates a node's
entire `clock-gates` list, providing a reason to test the full list; this does
not establish the iPadOS driver's policy or that unrelated links are required
for storage. The overlay compiled and applied to a local J71s test DTB; the original version set four link minimums and the DART node contained seven
domain phandles. The revised overlay must be validated separately. It has not been booted or tested for cleanup. The current kexec
loader retains its existing device tree, so this overlay is not applied merely
by building a new kernel. Power-domain activation may affect other peripherals;
restore and shutdown behavior must be validated before using it.

Update: the overlay now leaves the extra links' minimum-state fields alone.
The diagnostic driver must attach all seven listed domains using managed
power-domain links; the existing kernel explicitly requires four and will
reject this overlay until adapted. This avoids introducing new persistent
minimum-state settings for LINK1–LINK3, but successful attachment and cleanup
still require physical verification.
The revised overlay was compiled and applied to the local test DTB: it has
seven domain phandles and no `apple,min-state` property on LINK1–LINK3.

The overlay was updated to include both diagnostic opt-in properties, compiled
and applied to the test DTB. Without `orchard,shared-bits-test`, the seven
power domains would be requested but the link experiment would not run. The
matching kernel must expect seven domains; neither the image nor cleanup has
been physically tested.

`test-all-link-domains.sh J71S_DIAGNOSTIC_DTB` compiles and applies the overlay
in a temporary directory and checks the model, opt-in properties, ordered
seven-domain phandles and absence of new minimum states on LINK1–LINK3. It
requires `dtc`, `fdtoverlay` and `fdtget`; it does not boot a device. The test
passed against the prepared J71s tree and rejected a tree with unexpected
minimum states.

A software-only single-CPU handoff applied the seven-domain overlay to the
next boot's FDT and ran the diagnostic on J71s without DFU. All three extra
link domains reported active during the test; the 500 ms candidate link-state
poll still timed out at zero. Tested tuning and control restoration readbacks
passed. After probe cleanup, LINK1–LINK3 each reported actual, target and
minimum state zero, consistent with managed detach. The iPad remained
responsive. This does not prove a working link, hardware DMA or reversal of all
hardware effects. No PCIe host, physical DMA or storage command was used.

A follow-up sampled candidate port `0x88` before reset release, before
training, and after the bounded training attempt. Bit 0 was clear at the first
two samples and set afterward; bit 6 remained clear. The related driver's
candidate `0x208` state poll still timed out at zero. Extra link domains
reported active during the test and off after cleanup; reported control and
tuning restoration checks passed. This transition does not establish a
working link, endpoint discovery or DMA. No PCIe host, physical DMA or storage
command was used.

A further RAM diagnostic read the root port's standard PCIe link-status
fields around training. Beforeward they reported speed 1, width 1, training
clear and data-link-active clear. The bounded port `0x88` bit-0 poll succeeded;
a later standard status sample reported speed 2, width 2, training clear and
data-link-active set. The related driver's `0x208` state poll still timed out
at zero. This is evidence of a negotiated, active root-port link in the tested
sequence, not endpoint enumeration, working DMA or storage. Tested control and
tuning restoration readbacks passed, the additional link domains returned off
after cleanup, and the iPad remained responsive. No PCIe host, physical DMA or
storage command was used.

A read-only root-port bus-number sample during the active-link test reported
primary, secondary and subordinate bus numbers all zero. The standard link
status again reported speed 2, width 2 and data-link-active set. This shows
that no secondary bus was assigned in that test; it does not identify or
access the endpoint. Tested restoration readbacks passed, the extra domains
returned off, and the iPad remained responsive. No PCIe host, physical DMA or
storage command was used.

With the root link reporting active and its bus numbers initially zero, a
guarded test temporarily assigned secondary and subordinate bus 1. The new
value and restored original value both matched on readback. The root link
again reported speed 2, width 2 and data-link-active. Other tested control and
tuning restoration readbacks passed; the extra domains returned off and the
iPad remained responsive. This checks routing-register readback only, not
endpoint discovery or reversal of all effects. No endpoint read, PCIe host,
physical DMA or storage command was used.

A guarded follow-up temporarily routed bus 1 and performed one read of its
candidate device-0/function-0 PCI configuration ID. The endpoint responded with
vendor/device `106b:2002`. The original bus value and other tested controls
and tuning read back as restored, extra domains returned off, and the iPad
remained responsive. This identifies a responding PCI endpoint; its class,
functional DMA and storage access are not yet verified. No endpoint write,
PCIe host, physical DMA or storage command was used.

A guarded follow-up read the responding endpoint's PCI class/revision and
header type: `018002`, revision `11`, header `00`. The current kernel's NVMe
PCI ID table has no explicit `106b:2002` entry and its generic NVMe class
match does not match `018002`; adding an ID alone would not establish safe
controller or DMA behavior. The link was active during the read, tested
control and tuning restoration readbacks passed, extra domains returned off,
and the iPad remained responsive. No endpoint write, PCIe host, physical DMA
or storage command was used.

The endpoint's PCI command and BAR reads showed memory decoding and bus
mastering disabled, and BAR0 described a 64-bit, non-prefetchable memory
window with both address portions zero. The link was active and the bus and
other tested controls/tuning read back as restored; extra domains returned off
and the iPad remained responsive. The BAR size and controller behavior remain
unverified. No BAR sizing or assignment, endpoint write, physical DMA or
storage command was performed.

A guarded PCI BAR sizing operation, performed with memory decoding and bus
mastering disabled, reported a valid 16,384-byte 64-bit BAR. Both BAR words,
the bus register and other tested controls/tuning read back as restored; the
extra domains returned off and the iPad remained responsive. This is a BAR mask
measurement, not an assigned window, controller register access or proof of
complete side-effect reversal. No PCIe host, physical DMA or storage command
was used.

A subsequent read of the root bridge configuration found command `0x0000`,
non-prefetchable memory-window register `0x00000000`, and prefetch window
register `0x00010001`; root memory decoding was disabled. The endpoint BAR
sizing result repeated, and the diagnostic restored the tested registers. The
live Linux resource map showed no claimed resource at the candidate CPU
window, but unclaimed does not mean safe to access. The related J71b tree maps
PCI address `0xc0000000` to CPU address `0x7c0000000`, consistent with the J71s
captured controller ranges; actual J71s address routing remains unverified.
No BAR assignment, controller register access, DMA, or storage commands were
performed. The device remained responsive with 62% battery, discharging.

A guarded RAM-only diagnostic temporarily assigned the candidate PCI memory
window and the endpoint BAR with both memory decoding and bus mastering
still disabled. The bridge window and BAR values read back as written; both
BAR words, the bridge window, and the bus-number register subsequently read
back as restored. This confirms configuration-register readback, not working
CPU-to-PCI routing, controller MMIO, DMA, storage, or reversal of all side
effects. No controller registers or storage commands were accessed. The iPad
remained responsive at 61% battery, discharging.

A follow-up RAM-only diagnostic temporarily enabled PCI memory decoding on
the bridge and endpoint, with bus mastering disabled, and read the word at
controller offset `0x08`. It returned `0x00010001`, consistent with the NVMe
version register indicating version 1.0.1. Command words, BAR words, bridge
window and bus numbers all read back as restored, and the iPad remained
responsive at 61% battery, discharging. This supports controller MMIO access
for the tested read; it does not prove full NVMe compatibility, hardware DMA,
controller initialization or disk access. No DMA or storage command was issued.
The Linux definitions for [PCI command bits](https://github.com/torvalds/linux/blob/master/include/uapi/linux/pci_regs.h)
and [NVMe registers](https://github.com/torvalds/linux/blob/master/include/linux/nvme.h)
document the meanings used in this diagnostic.

The same guarded RAM diagnostic read controller CAP `0x00000020f00103ff`,
CC `0`, and CSTS `0`. Interpreted using the NVMe definitions, the controller
reports 4 KiB minimum and maximum controller page sizes and is not enabled or
ready at that point. The pinned Linux NVMe driver uses 4 KiB controller pages
independently of the kernel's 16 KiB CPU pages. All tested configuration
registers read back restored and the iPad remained responsive at 61%,
discharging. This does not prove controller initialization, hardware DMA,
scratch-memory setup or storage access.

A follow-up guarded read of BAR offsets `0x1808`, `0x180c`, `0x1824`, and
`0x1828` returned `0xe00000`, `0x1000`, `0x3`, and `0xff`, respectively.
If the definitions in the related [Corellium Hx driver](https://github.com/corellium/linux-sandcastle/blob/sandcastle-5.4/drivers/nvme/host/hx.c)
apply to S8000, these correspond to 14 MiB scratch, 4 KiB alignment, core mask
3 and a log-size field of 255. These are plausible candidate requirements,
not independently verified S8000 definitions or a working scratch setup. No
controller registers were written, DMA enabled or storage commands issued;
the tested PCI configuration read back restored, and the iPad remained
responsive at 61% battery, discharging.

A guarded read of the candidate Hx initialization and scratch configuration
registers found initialization zero, scratch address zero and scratch size
zero; the candidate boot state was neither all ones nor the Hx magic value.
This is consistent with no configured scratch region at those offsets during
this boot, but their S8000 meanings are not independently established. The
existing J71b branch includes an Apple ANS FlatDMA/NVMMU implementation;
S8000 still needs verified reserved-memory ownership, address translation,
interrupts and lifecycle before that implementation can be used. No scratch
configuration writes, DMA or storage commands were performed; tested PCI
configuration read back restored, and the iPad remained responsive at 60%,
discharging.

The allocation-only `j71s-nvme-scratch-reserve.dtso` requests a dynamically
allocated, 1 MiB-aligned, 14 MiB `no-map` reservation. Its size is based on
the observed candidate scratch request; the larger alignment matches the
related H9P driver's SART window requirement. The overlay neither supplies an
IOVA nor enables a controller or DMA. A synthetic-tree test and an offline
application to a private copy of the J71s tree passed; no physical boot has
used it yet, and real reservation, addressability and ownership remain
unverified.

The pinned kernel allocates dynamic reserved-memory nodes through memblock,
but a node with only `size` and `alignment` has no `reg` property added by
default. Consequently the existing J71b H9P and ANS paths, which call
`of_address_to_resource()` on the HMB node, cannot consume this reservation
as written. An S8000 adaptation must use `of_reserved_mem_lookup()` (and
validate base, size, alignment, ownership and cleanup), or explicitly supply a
verified static reservation. Changing only the overlay would not make the
existing driver work. No IOVA has been chosen and no DMA was tested.

The dynamic reservation was subsequently tested on the physical J71s using
a two-stage RAM-only kexec handoff. Linux's `of_reserved_mem_lookup()` found
a nonzero 14 MiB region aligned to 1 MiB; the boot log marked it `nomap` and
non-reusable, and it did not overlap System RAM resources in the observed
`/proc/iomem`. As predicted, `of_address_to_resource()` returned `-EINVAL`.
The existing controller-read diagnostic and PCI register restoration repeated,
and the iPad remained responsive at 60%, discharging. This establishes one
reservation and API lookup, not safe DMA or working storage. No IOVA, NVMMU
mapping, bus mastering, scratch programming or storage command was used.

`dynamic-hmb-driver.patch` is an experimental follow-up to the J71b driver
patch. It preserves the existing `reg`-based lookup and adds a shared helper
for a dynamic reserved-memory node only if it is `no-map`, non-reusable,
present, nonempty, and representable as a resource. Existing caller checks
still enforce their size, alignment, IOVA and ownership constraints. The
standalone `test-dynamic-hmb.py` compiles the actual patch helper and exercises
fixed lookup success/failure, dynamic lookup, missing/unsafe regions, and
address overflow; the follow-up patch applies cleanly to both extracted J71b
driver files. A J71s test kernel compiled the helper and called it on the
physical dynamic reservation: it returned success, the expected size and the
same base as `of_reserved_mem_lookup()`. The iPad remained responsive at 60%,
discharging. The full modified PCIe/NVMe drivers have not been built or run
on J71s; this is a lookup component, not proof of DMA or storage support.

The follow-up patch was additionally applied after **all** current J71b kernel
patches to the pinned Orchard Linux revision. With the J71b configuration run
through `olddefconfig`, the H9P PCIe object and both NVMe PCI/Apple ANS
objects compiled, and the NVMe objects linked into the combined `nvme.o`.
The resulting configuration differed from the checked-in configuration by
only the missing `CONFIG_CC_CAN_LINK=y`; therefore this is an object/link
check, not a clean reproducible full kernel build or a J71s hardware test.
The J71b PCIe driver matches T8010/J172 and contains SoC-specific common/PHY
sequences and tuning, so adding an S8000 match alone would be insufficient.

`extract-pcie-tunables.py` is an experimental, allocation-only host converter
for a locally captured Apple device tree. With `orchard_cli` importable, it
validates the common, PHY, port-0 and root-0 tables as 32-bit local records,
checks offsets against candidate window bounds and masks, and creates a new
mode-0600 DTS fragment. It refuses an existing destination; the generated
fragment contains device-derived data and must remain private. It does not
apply tuning or enable hardware. `test-pcie-tunables.py` covers synthetic valid
and malformed records.

On the private J71s tree the converter validated all four tables and the
fragment compiled with `dtc`. Its common (34 records), PHY (41) and port-0
(6) tables exactly match the values used by the previous successful physical
link diagnostics; the comparison was local and no device-derived values were
published. These `orchard,s8000-*` names are experimental handoff properties,
not an established binding. A PCIe driver must still consume them with
appropriate resources, sequencing, error handling and lifecycle; the root-0
table's use and full port remain unverified.

`driver-patch/include/linux/apple-s8000-tunables.h` provides an experimental
reader for the converter's three-cell offset/mask/value records. It requires
an exact bounded record count and validates the full table's alignment,
window bounds and mask/value relationship before a caller performs MMIO.
`test-s8000-tunables.py` exercises valid, missing, truncated, unaligned,
out-of-window, invalid-mask and read-failure cases. An isolated J71s test
kernel is being built to replace the earlier embedded common, PHY and port
arrays with these DT properties. Its private host MMIO mock passed the prior
link/rollback checks and rejects absent tables before register writes. A
private overlay injects the device-derived tables into the next RAM boot;
physical behavior and integration into a PCIe host driver remain unverified.

The DT-tunable reader was physically tested in an isolated RAM diagnostic.
A private overlay supplied this iPad's three tables to the diagnostic node;
the reader validated 34 common, 41 PHY and 6 port records before MMIO. The
root link then reported active at speed 2, width 2, PCI endpoint `106b:2002`
responded, and controller version read `0x10001`. The tested tuning-table and
early rollback paths reported zero errors, the scratch reservation remained
available, and the iPad remained responsive at 59%, discharging. A host mock
also verified that missing table input causes no diagnostic MMIO writes.
This checks the experimental DART-probe sequence using DT-supplied values,
not a finished PCIe host, physical DMA or usable storage. The device-derived
overlay and resulting handoff image remain private.

The reusable `apple-s8000-tunable-mmio.h` helper applies validated masked
register tables and restores saved registers in reverse order, including a
record whose write readback failed. Its host test covers successful updates,
inaccessible reads, mismatches, duplicate offsets, restoration failures and
invalid initial state; the full private diagnostic MMIO mock also passed.
The helper compiled into the J71s RAM diagnostic and physically applied all
41 early PHY and 34 common entries from the private DT data. The link again
reported speed 2/width 2/active, endpoint `106b:2002` and controller version
`0x10001` responded, and both helper rollback paths reported zero errors.
The iPad remained responsive at 58%, discharging. This validates the helper
in the isolated probe sequence, not a complete PCIe host or physical DMA.

A further RAM-only physical test used the same reusable masked-write helper
for **all five** early and later tuning stages. It applied the 41-entry PHY,
34-entry common and 6-entry port stages successfully, in addition to the
early 41/34 stages. The link reported active at speed 2/width 2, the PCI
endpoint and controller version responded, and all five reverse-restoration
paths reported zero errors. The full private MMIO mock passed its failure and
rollback cases, and the iPad remained responsive at 58%, discharging. This
confirms reusable tuning operations in the isolated diagnostic; a Linux PCIe
host, DMA translation and disk I/O are still unimplemented on J71s.

The complete isolated sequence was moved from the DART probe into a separate
J71s PCIe diagnostic platform driver in a private test kernel. Its DT overlay
disabled the test DART and software-only consumer, supplied the seven power
domains and private tuning properties to the PCIe node, and left DMA and PCI
host registration disabled. The host mock passed, and a two-stage RAM boot
physically repeated the active speed-2/width-2 link, endpoint and controller
reads, and zero-error tuning restoration with PCIe as the device owner. A
follow-up moved the two root-port settings from embedded values to the
validated private DT table, with their register offsets constrained; the
same physical checks passed. The iPad remained responsive at 57%, discharging.
This is a diagnostic platform driver and deliberately returns without
registering a PCI bus; it is not an I/O-ready host driver. Its experimental
source and device-derived data remain private while the source is audited.

A temporary PCI-core discovery test was integrated into the separate J71s PCIe
diagnostic. While the already-tested code held the link up and temporarily
routed bus 1, the test registered a short-lived host bridge with config reads
limited to bus 0/device 0 and bus 1/device 0, and rejected all PCI-core config
writes. It used `pci_scan_root_bus_bridge()` without `pci_bus_add_devices()`,
so normal PCI driver binding was not enabled, and removed the root bus before
the existing diagnostic restored its bus route and other settings. On the
physical iPad, the PCI core found endpoint `106b:2002`, reported no bound
driver, and removed the temporary host successfully. The subsequent controller
read worked, the BAR/bridge/bus and tuning restoration checks passed, and the
extra link domains returned off. The iPad remained responsive at 57%,
discharging. The diagnostic's own guarded bus/bridge/BAR writes are separate
from the scan's write-denial policy. This demonstrates PCI-core discovery, not
resource assignment, a persistent host, hardware DMA or disk I/O.

The experimental `driver-patch/j71s-pci-scan.h` contains the scan code;
`test-j71s-scan-policy.py` checks its address limits and write-denial callback.
The source is an isolated experiment, not a production PCI host driver.

A subsequent short-lived PCI-core scan permitted only guarded BAR0/BAR1
sizing writes to the known `106b:2002` endpoint. It required an unassigned
BAR and disabled endpoint/root memory decoding and bus mastering before
starting, denied other PCI-core writes, and did not bind drivers. On the iPad,
PCI core reported a 16,384-byte memory BAR, four permitted sizing/restoration
writes, and both BAR words restored. Host removal and the surrounding
PCIe diagnostic's restoration checks passed; the controller still responded
and the iPad remained responsive at 57%, discharging. This confirms PCI core
can size the resource, not that it can assign a working host window or perform
DMA or disk I/O. `driver-patch/j71s-pci-bar-scan.h` and its host guard test
capture this diagnostic policy; they are not a production driver.

A temporary resource-assignment test extended the PCI-core scan. It claimed a
1 MiB CPU memory window corresponding to the candidate PCI bus window, set
the root bridge memory aperture with decoding disabled, scanned without driver
binding, then asked `pci_assign_resource()` to assign the 16 KiB endpoint BAR.
The PCI write policy permitted only the known BAR sizing, restoration and
candidate address values while endpoint memory decoding and bus mastering were
off. On the physical J71s, PCI assignment returned 0, the resource's CPU start
and the endpoint BAR read back as expected, the upper BAR was zero and bus
mastering remained off. The temporary host, BAR and bridge window were removed
or restored; a subsequent controller read and the diagnostic's bus/tuning
restoration checks succeeded. The iPad remained responsive at 56%, discharging.
This tests PCI resource assignment, not persistent host operation, DMA or
storage I/O. `driver-patch/j71s-pci-assign.h` and its guard test capture the
experimental implementation; it retains the allocation if resource release
fails to avoid leaving a dangling resource pointer.

A follow-up RAM-only test used `pci_iomap()` on the PCI-core-assigned endpoint
BAR. After confirming the expected resource and BAR readbacks, it temporarily
enabled root and endpoint memory decoding, with bus mastering disabled, and
read the controller version through the PCI mapping. The physical read returned
`0x10001`, the root and endpoint command words, BAR and bridge window read
back restored, and the link-tuning cleanup reported zero errors. No PCI driver
was bound and no DMA or storage command was issued. The iPad remained responsive
at 56%, discharging. The host test covers invalid state, mapping failure and
rejected decode enables; `driver-patch/j71s-pci-iomap.h` is experimental test
code, not a persistent host or a complete failure-recovery implementation.

A follow-up diagnostic moved the PCIe sequence into delayed work and held the
PCI-core-discovered, assigned endpoint for a bounded 20-second window after
Linux started. The PCI device appeared in sysfs with vendor/device `106b:2002`,
a 16 KiB BAR at the expected CPU address and no bound driver. After the window,
the host and PCI devices disappeared, BAR/bridge/tuning restoration checks
passed, and extra PCIe power domains returned off; the iPad remained responsive
at 56%, discharging. The diagnostic still does not call `pci_bus_add_devices()`,
start a storage driver, enable bus mastering or issue disk commands. Its worker
has a shutdown wakeup/cancel path, but shutdown during the active window has not
yet been physically tested. `driver-patch/j71s-pci-held.h` captures the bounded
scan variant, and `observe-pci-held.sh` is the observation script. This is not a
persistent PCIe host or an I/O-ready driver.

The active-window cancellation path was exercised on the physical iPad. After
unbinding and rebinding the diagnostic, the PCI endpoint became visible again;
unbinding during the 20-second window returned in under one measured second,
removed the PCI devices and reported successful BAR, bridge and tuning
restoration. Extra link domains subsequently reported off, and the iPad
remained responsive at 55%, discharging. The driver's remove and shutdown
callbacks share the same wakeup-and-cancel function, but this test exercises
remove via sysfs; a real reboot or kexec during the active window has not yet
been tested. `test-active-pci-unbind.sh` records the device-side procedure.
No storage driver or DMA was enabled.

The worker experiment was extended to keep the assigned but unbound PCI
endpoint present until an explicit stop, releasing the global PCI rescan/remove
lock while waiting. On the physical iPad, sysfs still showed `106b:2002`, the
expected 16 KiB resource and no driver after 25 seconds. A checksum-verified
RAM-to-RAM kexec was then initiated with the host active; a fresh kernel came
up and successfully rediscovered and mapped the endpoint. A subsequent active
unbind returned, removed the PCI devices and reported successful BAR, bridge
and tuning restoration. This is evidence that one active-host kexec and
reinitialization worked; the previous kernel's shutdown messages were not
captured and complete reversal of hardware side effects remains unproven.
The iPad was at 55%, discharging. No PCI driver, bus mastering, DMA or disk
commands were enabled. `driver-patch/j71s-pci-persistent.h` and the observation
and stop scripts are experimental; the workqueue-owned host is not yet a
production driver and its behavior under unrelated concurrent PCI removal has
not been validated.

The persistent host experiment was extended with an isolated diagnostic PCI
driver matching the iPad's storage endpoint only when attached to the J71s
test host. The host permits the endpoint's memory-enable/disable command but
rejects bus-mastering and unrelated configuration writes. On the iPad,
`pci_bus_add_devices()` bound `j71s-nvme-readonly-test` to `106b:2002`; the
driver used `pci_enable_device_mem()` and `pci_iomap()` and read controller
version `0x10001`, with bus mastering off. Active platform-driver unbind then
invoked PCI driver removal, restored its command register, removed the PCI
devices, restored root command/BAR/bridge state, and reported zero tuning
rollback errors. The iPad remained responsive at 54%, discharging. This is a
diagnostic register-read driver, not an NVMe storage driver; no DMA or disk
command was issued. The experimental implementation and host config-policy
test are `driver-patch/j71s-pci-driver-test.h` and
`test-j71s-driver-policy.py`.

A diagnostic PCI-driver follow-up checked the dynamically reserved scratch
region through a CPU mapping. After verifying the `no-map`, non-reusable,
14 MiB, aligned reservation and absence from System RAM resources, it saved,
pattern-tested and restored three 64-bit locations. On the physical iPad all
three patterns and restorations matched. While the PCI link was active it also
read candidate NVMMU offsets `0x20`, `0x24`, `0x28`, and `0x2c`: control and
physical fields were zero, the two candidate range fields were nonzero, and
none was all ones. These fields may contain retained state; their S8000
semantics are not proven and their values were not reused. Driver removal and
the tested PCI cleanup succeeded. The iPad remained responsive at 54%,
discharging. No translation registers were written, bus mastering enabled or
storage command issued. The code and host guards are in
`driver-patch/j71s-scratch-test.h` and `test-j71s-scratch-ram.py`.

An isolated test attempted to write three candidate NVMMU window fields using
address formulas from the related H9P driver and the Linux-owned scratch region.
It required controller CC/CSTS zero, PCI bus mastering off, a valid no-map
scratch reservation and candidate control offset `0x20` equal to zero; it did
not write the control register or issue DMA. On the iPad the first field at
`0x24` changed, but did not read back the requested value; it was neither zero,
unchanged nor all ones. The test stopped before writing the other two fields,
reported control still zero and restored the saved field with zero restoration
errors. The subsequent PCI driver removal and register cleanup succeeded, and
the iPad remained responsive at 54%, discharging. The H9P formula or register
semantics cannot be assumed for S8000; this result does not prove why the
readback differs, or that translation is functional. Host mocks cover disabled
control, DMA guards, mismatch and reverse restore. The experimental test is
`driver-patch/j71s-nvmmu-window-test.h`.

A private follow-up examined the first candidate NVMMU window field (`0x24`)
without enabling its control. In the prior candidate write, the observed
value equaled the requested value OR the previously set bit 31; the other
requested set bits appeared in readback. A second test wrote zero to this
field only, and readback still had bit 31 set and equaled the saved baseline.
Both tests reported control off and successful restoration, followed by
successful PCI and tuning cleanup. The iPad remained responsive at 53%,
discharging. These two observations are consistent with a forced or retained
high bit, but do not establish all writable bits, the meaning of the field,
or the address-translation format. The underlying register samples remain
private; no DMA or disk command was issued.

A guarded follow-up checked the remaining candidate NVMMU fields with control
and PCI bus mastering still off. The first two range registers read back as the
requested H9P-formula values with bit 31 set; the third candidate physical
field read back the requested Linux scratch-region value. All three saved
fields restored with zero reported errors and the control remained zero. The
readback and restore behavior does not establish address translation, register
semantics, or safe DMA. The PCI diagnostic unbound and its tested settings
restored. A first battery read returned I/O errors, then the battery reported
53% and discharging on recheck. `driver-patch/j71s-nvmmu-three-fields.h` and
its host test capture the experiment; the public copy omits the private raw
mismatch logging used for local analysis.

A guarded follow-up programmed the three candidate window fields using the
observed readback rules, then briefly wrote `1` and `0` to candidate control
`0x20`. It required the NVMe controller CC/CSTS and candidate TCB control to
be zero, bus mastering off, a validated reserved scratch region, and matching
window readbacks. The iPad read back control enabled and then disabled; all
three window fields restored with zero reported errors. The diagnostic PCI
driver then unbound and the tested PCI/tuning state restored; the iPad remained
responsive at 52%, discharging. Host tests include a simulated control-disable
failure, in which the code deliberately leaves the fields in place rather than
rewriting them while control appears enabled. This is control/register
readback only, not evidence that translation works or DMA is safe. No PCI bus
mastering or storage command was enabled. The experimental implementation is
`driver-patch/j71s-nvmmu-enable-test.h`; its public copy omits private raw
mismatch logging.

A guarded integration test configured the candidate NVMMU window from the
Linux-owned scratch reservation, enabled candidate control, and temporarily
wrote the corresponding candidate IOVA and size to the controller's scratch
registers. It required CC/CSTS zero, PCI bus mastering off and zero scratch
register baselines; it issued no NVMe commands. On the iPad all three scratch
registers read back as written and restored with zero errors. NVMMU control
read back enabled then disabled, its three window fields restored, and the PCI
driver and host cleanup checks passed. Battery reads initially failed, then
reported 52% and discharging. This demonstrates configuration-register
readback, not that the controller can translate or access scratch memory.
The experimental source and host failure/restore tests are
`driver-patch/j71s-controller-scratch-test.h` and
`test-j71s-controller-scratch.py`; raw device-derived mismatch logging is
omitted from the public copy.

A RAM-kernel diagnostic allocated five candidate controller support buffers
through the PCI device's coherent DMA API, checked CPU-side patterns and DMA
address alignment, freed the buffers, and restored the original DMA masks. On
the iPad all five allocations and checks succeeded, with PCI bus mastering off
and controller CC/CSTS zero. The diagnostic unbound and the tested PCI and
tuning cleanup succeeded; battery reported 52% and discharging on recheck.
Host mocks cover partial allocation failure, coherent-mask failure and the
bus-master guard. No buffer addresses were given to the hardware and no DMA
or storage command was issued. This validates software allocation only; it does
not establish that the controller can access the buffers. The experimental
source and host test are `driver-patch/j71s-dma-alloc-test.h` and
`test-j71s-dma-alloc.py`.

The H9P implementation allocates its NVMMU translation tables for the PCI
host platform device, whereas the first allocation experiment used the PCI
endpoint. A follow-up ran the same software-only allocation test for both
separately. On the iPad each device allocated all five buffers, passed CPU
pattern and alignment checks and restored its DMA masks; PCI bus mastering
remained off. The test host unbound with its cleanup checks passing, and the
battery reported 51% and discharging. This does not compare the two devices'
DMA address translations, prove either path can access memory, or validate
NVMMU table contents; no hardware was given the allocated addresses.

The source-level integration boundaries for the PCI host, DART and ANS
translation paths are summarized in `storage-integration.md`. An executable
policy check confirms the current diagnostic rejects the configuration writes
and bus mastering needed by ANS preinitialization. The diagnostic therefore
cannot run the unmodified storage driver merely by binding it; normal PCI
configuration, DMA attachment and interrupts remain to be implemented and
tested.

A temporary combined PCIe/DART diagnostic explicitly created the disabled
DART node as a platform device only while the already-tested PCIe link and
power sequence were active. The DART driver initialized, then the diagnostic
host discovered and bound its register-only driver to the storage endpoint
with bus mastering off. The DART was present but the PCI endpoint had no
IOMMU group: the host did not supply a requester-to-DART mapping. Stopping the
host removed the endpoint, unregistered the DART before releasing the tested
PCIe controls, and reported successful tested restoration; the DART device
was absent afterward. Battery was 51% and discharging. Host mocks cover device
creation failure, existing-device and node guards, unbound driver, and cleanup.
This bypass of the disabled-node status is a controlled experiment, not a
production DT or lifecycle design; it did not attach an endpoint to the DART,
perform physical DMA, or issue a storage command. The isolated lifecycle
snippet and mock are `driver-patch/j71s-dart-coexist.h` and
`test-j71s-dart-coexist.py`.

A follow-up temporary changeset enabled the already-created DART node and
added a candidate PCI `iommu-map` for requester 0x100 to DART stream 0, using
the related J71b mapping as a hypothesis. With the test PCIe host active,
Linux placed endpoint 0000:01:00.0 in IOMMU group 0, and the endpoint's five
coherent allocations completed with CPU-side pattern and alignment checks.
The kernel also logged that requester ID 0x0 (the root bus device) had no
translation; the test did not map it. Bus mastering stayed off. On unbind the
PCI devices and DART were removed, the changeset reverted successfully, the
temporary properties were absent, DART status returned to disabled, and the
tested PCIe restoration checks passed. Battery was 50% and discharging.
Host mocks exercise the candidate mapping values and lifecycle/failure guards.
This establishes Linux's software attachment and allocator behavior only:
the physical requester-to-stream relationship, actual DMA translation and
storage operation remain unverified. The dynamic changeset and forced
instantiation are test infrastructure, not a proposed production binding.
The experiment is `driver-patch/j71s-dart-map-test.h`, with
`test-j71s-dart-map.py`.

With the candidate endpoint-to-DART software attachment active, the PCI
endpoint's diagnostic driver allocated a RAM page and mapped it with the DMA
API. `iommu_iova_to_phys()` returned the expected first and last physical
bytes; after unmap the lookup returned zero. Bus mastering and controller
CC/CSTS remained off. The PCI/DART diagnostic unbound, its DT changes reverted
and tested PCIe cleanup passed; battery was 50%, discharging. Host mocks cover
missing domains, allocation and mapping failure, mismatched lookups, unmap and
page cleanup. These lookups inspect software page tables; they do not test
hardware DMA, validate the physical stream selection, or issue disk commands.
The experiment and mock are `driver-patch/j71s-endpoint-map.h` and
`test-j71s-endpoint-map.py`.

The related J71b H9P FlatDMA code encodes each supplied physical address as a
32-bit 4 KiB page number, but previously did not reject misaligned addresses or
page numbers wider than 32 bits before truncating them. The experimental
`h9p-validate-pages.patch` rejects either condition before changing any TCB or
SGL; zero-page unmap requests remain accepted. The actual helper passes
`test-h9p-page-validation.py` for aligned boundaries, a null page list,
misalignment, overflow and a bad entry after a good one. The patch applies to
the extracted J71b source after the dynamic HMB experiment, and the modified
H9P object compiled with the existing kernel toolchain. It has not been run on
hardware and does not establish J71s FlatDMA semantics or working storage.

The J71s Apple DT contains PCIe MSI parent, address, vector offset and
per-port vector ranges. `extract-pcie-msi.py` validates property sizes, the
AIC parent, address alignment, bounds and non-overlap, then writes a new
mode-0600 private DTS fragment without printing the device-derived values.
A synthetic-input test covers malformed metadata and overlaps; the private
fragment from the connected iPad compiled with `dtc`. Its vector offset is
different from the J71b test tree, so the J71b MSI interrupt start must not be
copied blindly. The root has 32 vectors and port 0 has eight; the MSI address
matches the related J71b candidate. These are firmware-data observations,
not evidence of delivered interrupts. In particular, the relationship between
the Apple vector offset, PCI MSI message data, and Linux AIC interrupt
numbering still needs verification on S8000 before enabling MSI. The
extraction code does not configure or write any hardware.

The candidate port-0 MSI range was compared offline with interrupt words in
the captured Apple DT; none fell within the range. This is a conservative
word-level comparison, not proof of system-wide ownership. A RAM-only kernel
used the AIC domain to translate and temporarily allocate all eight candidate
vectors, rejecting an existing mapping and disposing newly allocated mappings
in reverse order. The iPad reported eight allocated out of eight, with no
error; the subsequent PCI endpoint still attached and bus mastering remained
off. The diagnostic host and DART stopped, the temporary IOMMU changes reverted
and tested PCIe cleanup passed. Battery was 49%, discharging. Host mocks cover
conflict and partial-allocation cleanup. No handler was registered and no MSI
was sent; vector allocation does not validate actual interrupt delivery, MSI
message data or the PCI MSI domain. The general test source and mock are
`driver-patch/j71s-msi-domain-test.h` and `test-j71s-msi-domain.py`;
device-derived constants remain private.

A read-only PCI capability inspection found a standard 64-bit MSI capability
with up to eight vectors and no MSI-X capability on this endpoint. An
experimental port-0 PCI MSI parent domain was then created with the candidate
AIC range and doorbell, attached to the diagnostic host bridge, and exposed to
the endpoint. On the iPad the domain creation succeeded and the bound
register-only endpoint driver observed an MSI domain; active unbind removed the
endpoint and domain, and tested PCIe/DART cleanup passed. Battery was 48%,
discharging. Host mocks cover one-vector allocation/free, rejected devices and
multiple vectors, exhaustion and parent-allocation rollback. No MSI vector was
allocated by the PCI endpoint, no MSI capability was enabled, and no interrupt
was delivered. The domain's message encoding and physical interrupt routing
remain unverified, and it is not yet a production PCI host implementation.
The source and mock are `driver-patch/j71s-msi-host-test.h` and
`test-j71s-msi-host.py`; device-derived values remain private.

A guarded follow-up allowed only the endpoint's MSI configuration writes and
INTx-disable command changes needed for a one-vector test, while keeping PCI
bus mastering and controller CC/CSTS off. `pci_alloc_irq_vectors()` returned
one vector; the MSI enable bit, candidate message address and data read back
as expected. After `pci_free_irq_vectors()`, the enable bit was clear and the
saved capability and command values were restored. On device the checks
reported `ret=1 matching=1 disabled=1 restored=1`; the PCI host, DART and MSI
domain then unbound and the tested cleanup passed. Battery was 48%,
discharging. Host mocks cover the write policy, missing domain, allocation
failure and failed-disable handling. No interrupt handler was installed and no
MSI was sent, so the physical interrupt route and message encoding remain
unproven. The diagnostic and policy snippets and tests are
`driver-patch/j71s-msi-alloc-test.h`, `driver-patch/j71s-msi-alloc-policy.h`,
`test-j71s-msi-alloc.py` and `test-j71s-msi-alloc-policy.py`.

Source review found that the existing J71b NVMe read-only command policy,
DMA-armed failure retention and reset/shutdown restrictions were conditioned
on the J71b machine compatible. Binding the driver on J71s without adaptation
would not enable those J71b-specific safeguards. The experimental
`j71s-nvme-readonly-guard.patch` extends those paths to J71s behind a separate
`j71s_ro_test` boot/module opt-in. On J71s it rejects the J71b read-write and
read-only switches; the J71b mode selection remains separately checked. Its
actual helper passed an exhaustive host-side model/opt-in matrix, and the
modified NVMe PCI and ANS objects linked as `nvme.o` in the extracted J71b
kernel tree. The patch does not add a J71s PCI host, change kernel/device-tree
boot configuration, or start the NVMe driver. It has not been exercised on
hardware and is not proof that DMA can be stopped or that the controller works.

The current [upstream J71t PCIe/NVMe proposal](https://github.com/OrchardLinux/hardware/pull/6)
allocates 128 TCB entries because the hardware may index that many, even though
software uses fewer request slots. It also requires a MiB-aligned scratch size
and bounds the SART window. `h9p-nvmmu-bounds.patch` carries these two checks into
the extracted J71b-based experimental driver. The actual scratch-range
predicate passes boundary/misalignment tests, TCB sizing covers all 128 entries
for both 4 KiB and 16 KiB kernel pages, and the modified H9P object compiles.
The tested iPad kernel uses 16 KiB pages, so its previous page-rounded TCB
allocation was already 16 KiB; this change makes the hardware requirement
explicit and covers smaller page sizes. The checks and 128-entry assumption
come from the related J71t implementation and are not independently proven for
S8000. This patch does not start the controller or test physical DMA.

A guarded NVMMU table-address test allocated two zeroed host DMA buffers,
required controller CC/CSTS, PCI bus mastering, TCB control and SART control
to be zero, then wrote and read back the four candidate table/base address
fields in the sequence used by the related J71t implementation. An initial
attempt stopped before writes because two saved table fields were nonzero.
A revised test saved those nonzero values (their origin is unknown), verified
all four candidate writes and restored every field. On the iPad it reported
`matched=1 restore-errors=0 retained=0 baseline-nonzero=2`; DMA masks restored,
and PCI/DART cleanup checks passed. Battery was 47% and discharging. Host mocks
cover allocation failure, mismatched writes, nonzero/all-ones baselines and
retention of buffers if restoration fails. No NVMMU initialization command,
PCI bus mastering, physical DMA or disk command was issued. This is register
readback only, not proof that the NVMMU can fetch these buffers or that
restoring register values reverses every possible side effect. The experiment
and mock are `driver-patch/j71s-tcb-address-test.h` and
`test-j71s-tcb-address.py`.

An **unbooted** one-shot NVMMU initialization experiment has been prepared.
It requires controller CC/CSTS and PCI bus mastering off, a host device without
an IOMMU domain, 36-bit DMA masks, and independently checked identity mappings
for two zeroed Linux-owned buffers. It saves and checks the four table address
registers before writing candidate addresses. Immediately before the candidate
`0x10000` initialization command it requires a special test kernel with kexec
loading disabled from startup and no preloaded normal or crash image. Once the
command is issued, both buffers remain allocated for the rest of that kernel's
lifetime, including on timeout; the diagnostic platform driver also suppresses
sysfs bind/unbind. A physical reset is required before running another test.
Before arming, error paths restore the saved fields and retain buffers if
restoration is uncertain. The bounded poll checks both the bit used by the
related J71b driver and the different bit used by the J71t driver; a clear
readback alone would not prove physical DMA or successful initialization.
Host mocks cover the guards, non-identity DMA, allocation failures, readback
failure and retained buffers on both apparent completion and timeout. The
kernel compiled locally, but this experiment has not been run on an iPad and
is not a production safety or teardown mechanism. The one-shot helper and
mock are `driver-patch/j71s-tcb-init-test.h` and `test-j71s-tcb-init.py`; the
helper depends on the special local kernel's kexec guard.

Before physical use, the prepared test was updated to zero both retained
buffers explicitly and report whether either changed after the initialization
command. A host mock verifies that the reports detect simulated changes, in
addition to the earlier guards. These observations do not establish that the
controller read either buffer: a DMA read leaves no changed bytes. Both normal
and file-based kexec load paths were checked against the special kernel's
startup lock. The revised kernel is built but remains unbooted.

While the one-shot boot remained pending, a separate reversible preflight
allocated the same sizes with a 36-bit mask on the PCI host device and checked
that each DMA address corresponded to the allocated physical memory via a
single-entry scatterlist. On the iPad it reported `identity=1 buffers=1
masks-restored=1`; PCI bus mastering remained off and normal PCI/DART cleanup
passed. Battery was 46%, discharging. This verifies those prerequisites for
one allocation in the running kernel, not a guarantee for a future allocation
or a hardware DMA test. The preflight and mock are
`driver-patch/j71s-tcb-preflight.h` and `test-j71s-tcb-preflight.py`.

For local reproducibility, `tcb-init-local-lockdown.patch` captures the four
special-kernel integration changes relative to the preceding private
TCB-address diagnostic source: disabled kexec loading, the guard declaration,
suppressed diagnostic bind/unbind and the one-shot helper call. Its application
was replayed on copies of those four files and matched the built source. It
requires the separately provided `driver-patch/j71s-tcb-init-test.h` and the
preceding diagnostic source; it is not a standalone or production patch.
`test-tcb-init-lockdown.py` checks the coupled guard and retention ordering.

The one-shot initialization kernel was subsequently booted on the iPad.
It reported `armed=1 poll=0 ctrl-zero=1 bit16=0 bit4=0 all-ones=0
 tcb-changed=0 table-changed=0 buffers-retained=1`. Thus the candidate command
was written and a bounded poll observed the selected bits clear; the two
zeroed buffers did not visibly change. That does not prove the command was
accepted, that hardware read them, or that DMA or storage works. The PCI
endpoint remained responsive with bus mastering off. Runtime checks showed
`kexec_load_disabled=1`, no loaded kexec image, and the diagnostic unbind
attribute absent. Battery was 45%, discharging. The two buffers intentionally
remain allocated in this kernel; physical reset is required before further
kernel tests. The compiled image was also regenerated from its `vmlinux` and
matched byte-for-byte; GDB showed the built-in kexec lock set and bind/unbind
suppression enabled.

A reusable, hardware-independent ANS TCB builder is provided in
`driver-patch/include/linux/apple-ans-tcb.h`, with a follow-up integration diff
`h9p-tcb-builder.patch` against the extracted J71b driver after the earlier page
validation and NVMMU bounds changes. It prepares the same TCB, SGL and FlatDMA
values as that driver while rejecting invalid tags, unaligned or unrepresentable
physical pages and SGL-address overflow before modifying the buffers. The
existing unmap/invalidate path remains with the caller. Golden-value tests
cover ordinary and maximum requests, invalid inputs and failure atomicity; the
modified H9P object compiled and the integration patch replay matched its source.
This is software preparation only. The descriptor format and DMA behavior have
not been validated on J71s, and the header and patch do not provide a working
PCI host or storage driver by themselves.

A further review of the newer J71t NVMMU implementation found a significant
difference from the older J71b reference: J71t uses exactly one TCB direction
per request and publishes the page count last, after a DMA write barrier.
The reusable builder now accepts explicit read, write, or legacy bidirectional
flags, validates the selection, and publishes the count after the other fields.
The existing J71b integration deliberately retains its prior bidirectional
flags; it must not be mistaken for a verified J71s request mode. Tests exercise
both single-direction encodings, legacy encoding, publication ordering and
failure atomicity, and the modified H9P object compiled. The S8000 hardware
semantics and safe slot retirement remain unverified.

`j71s-tcb-direction.patch` builds on that integration and passes the NVMe
request DMA direction to the descriptor builder. For the experimental J71s
path, a device-to-memory request selects the J71t-derived write flag and a
memory-to-device request selects the read flag. Other machines retain the
existing bidirectional behavior. Both modified kernel objects compile and the
builder tests cover the individual flags. This remains a candidate: neither
J71s DMA nor descriptor retirement has been validated on hardware, and this
patch alone does not make storage access safe.

The current J71t driver constrains one-cell PCI DART consumers to a DMA IOVA
window distinct from the FlatDMA, scratch and MSI ranges. Without a comparable
constraint, our earlier software-only endpoint mappings could use addresses
that are unsuitable for real controller traffic. The J71s Apple DT's DART0
`vm-offset` contains two 32-bit offsets and one shared `vm-size`; the first
candidate and size match the related J71t window. The storage endpoint refers
to the expected DART0 mapper, but the relationship between the two Apple
metadata offsets and the actual S8000 requester stream is not established.

`extract-dart-window.py` checks the private tree's mapper relationship and
candidate shape and writes a new private mode-0600 fragment. The experimental
`dart-one-cell-window.patch` and
`driver-patch/include/linux/apple-dart-dma-window.h` add a validated optional
`apple,dma-range` to a private test DART driver and use it for one-cell
consumers; five-cell consumers retain their explicit-window path. Host tests
cover malformed metadata, alignment, arithmetic overflow and masks; the
modified DART object and a private test kernel compiled. This device-tree
property and the temporary test changeset are experimental, not an upstream
binding. A private RAM boot image with the candidate has been assembled but not
yet run. None of the software evidence proves the physical stream mapping,
hardware DMA or storage functionality.

The private bounded-window RAM image was booted directly from DFU on the iPad.
The DART initialized and Linux attached the PCI storage endpoint to its IOMMU
group. The endpoint's software page-map test reported `first-match=1
last-match=1 unmapped=1 aperture-match=1 iova-in-window=1`. The latter checks
show the requested candidate aperture and the allocated IOVA agree in Linux's
software state; they do not establish the actual S8000 hardware stream or DMA
routing. The diagnostic unbound with no PCI devices left; both temporary DT
changesets reported successful reversion and tested PCIe restoration passed.
Battery initially returned I/O errors, then reported 43% and discharging. No
physical DMA or disk command occurred. `dart-window-coexist.patch` records the
private test's generic changeset and observation integration, relative to the
preceding diagnostic source; it also needs a private header containing the
candidate values and the separately supplied DART window patch. This is test
infrastructure, not a standalone driver or proposed production binding.

A read-only PCI extended-capability scan of the iPad storage endpoint found
LTR at offset `0x178` and L1 PM substates at `0x180`; its current L1SS control
values matched neither the J71b setting nor the candidate S8000/J71t setting.
No capability was written during this scan. `j71s-ans-pci-config.patch`
changes the extracted J71b-based ANS glue to discover those capabilities
rather than assuming fixed offsets, and chooses the related J71t driver's
S8000 candidate control value only on J71s. Missing capabilities and config
write failures return errors; the patch does not roll back earlier successful
writes after a later failure. Host mocks cover capability locations, both
model settings and each failure position. The candidate is not validated on
S8000 hardware.

Source review also found that the inherited NVMe PCI code enabled bus
mastering before checking controller state. The separate experimental
`j71s-nvme-master-guard.patch` requires J71s PCI bus mastering already off and
CC/CSTS both zero before enabling it. Host tests exercise config-read failure,
preexisting mastering and active/nonzero controller states. This guard does
not prove an inherited active device is safely stopped, protect against every
race or replace a complete host isolation and teardown design. Both changes
compiled together as `nvme.o`; neither was run on hardware. The raw captured
PCI configuration remains private.

A guarded RAM-kernel test attempted the J71t-derived PCI configuration
sequence while PCI bus mastering and controller CC/CSTS were off. The first
attempt stopped at the legacy latency-timer byte: the write and read calls
succeeded but the readback differed from `0x40`. Its original zero baseline
was restored; the differing value was not recorded, so the test does not prove
that the byte remained zero. A follow-up left that byte untouched and tested
LTR, L1SS control 2 and the candidate S8000 L1SS control 1. All three read back
as requested, and the saved values restored with zero reported errors. The
PCI host unbound, no PCI devices remained and the tested PCIe cleanup passed.
Battery was 41%, discharging. Host mocks cover the restricted write policy,
partial failure including a simulated failed write with side effects, and
reverse restoration. No controller DMA or storage command was issued; these
are config-register readbacks, not proof the settings are correct during I/O.
The diagnostic and mocks are `driver-patch/j71s-ans-config-test.h`,
`driver-patch/j71s-ans-config-policy.h`, `test-j71s-ans-config-test.py`, and
`test-j71s-ans-config-experiment-policy.py`.

The experimental ANS PCI configuration patch now leaves the legacy latency
timer unchanged on J71s, following the readback mismatch above. J71b retains
its previous timer write. The three J71s candidate LTR/L1SS values have passed
one disabled-controller write/read/restore test, but remain unproven during
actual storage I/O. The updated capability and failure-path mock passed for
both variants, and the modified NVMe object compiled; the full NVMe driver has
not been run on this iPad.


The private J71s Apple device tree's `nvme-mmu0` node contains an
`invalidate-fifo-workaround` value of 1. In a separate read-only diagnostic,
with the PCI endpoint enumerated and the NVMe controller disabled, the port
register at the J71t-derived FIFO status offset was readable and bit 0 was 1.
This is consistent with the related driver's idle FIFO indication, but does
not establish the meaning of the bit or prove invalidation completion. The
first attempt unbound before asynchronous enumeration completed; the successful
attempt waited for the endpoint. No NVMe command or DMA was issued.

`j71s-nvmmu-fifo-candidate.patch` is an experimental follow-up to
`j71s-tcb-direction.patch`. It tracks used descriptor slots, skips invalidation
for never-mapped slots, serializes and polls the candidate FIFO, and returns an
error and retains the slot on timeout. It polls after writing the invalidation
as an additional observation, but an empty status read does not itself prove
that the write reached the hardware or that a cached translation was retired.
Concurrency, DMA teardown, the status semantics and safe reuse remain
unverified. The H9P object compiled; this candidate has not been run on J71s
and is not an I/O-ready driver.


`j71s-host-one-shot-guard.patch` is a local experiment layered on the
candidate FIFO and descriptor patches, not a general-purpose upstream kernel
change. It starts the experimental kernel with kexec loading disabled, checks
that no kexec image is loaded and that the PCI host is not using an IOMMU,
checks the three host-allocated descriptor buffers have identity DMA addresses
within 36 bits, and requires the candidate NVMMU and SART control registers to
be zero before table addresses are written. It pins the host module before
arming; the existing host code retains its table allocations. This closes some
early ownership gaps before NVMe setup, but it does not establish that the
NVMMU, SART, PCI device, queues or later teardown are safe. The candidate
register semantics and live DMA remain unverified. The host and kernel objects
compile; the patch has not been booted or tested on the iPad. A physical reboot
is required after a one-shot test that arms hardware.


A one-shot J71s RAM diagnostic issued the J71t-derived tag-0 invalidation
command after initializing zeroed retained TCB tables. The endpoint's bus
master and controller remained disabled. The candidate FIFO status polled
empty before and after the write (`before=0 submitted=1 after=0
status-valid=1 empty-bit=1`); the test's kexec lockdown was enabled and its
buffers were retained. `j71s-tcb-fifo-once.patch` captures this follow-up
against the prior one-shot test source. The status may read empty before a
posted write reaches the hardware, and there was no cached translation or DMA
operation to verify. Consequently this result does **not** prove command
completion, invalidation, safe reuse, or storage I/O. A physical restart is
required before the next hardware boot.


`j71s-retire-fail-closed.patch` follows the FIFO and one-shot ownership
candidates. Because the observed empty bit cannot prove the posted invalidate
completed, a J71s retirement now returns an error and poisons the path even if
both FIFO polls pass. The descriptor slot and caller's payload must remain
allocated until a physical reset. It also fixes the NVMe metadata-mapping
failure path to retain a request if data retirement failed during cleanup.
The modified PCI host and NVMe objects compile. This deliberately prevents a
normal completed storage request: a separate controlled observation mechanism
and evidence of safe retirement are still needed. It does not make the current
experimental driver safe to boot as a complete storage stack.

`driver-patch/j71s-identify-preparation.h` prepares a one-command Identify
Controller admin queue, completion queue, and 4 KiB payload allocation. It
requires candidate endpoint DMA addresses inside the provisional DART window,
extracts and bounds-checks the payload's physical page for the candidate
FlatDMA descriptor, and encodes a tag-zero candidate FlatDMA command. The
allocation-release helper is only for the unarmed state. The code does not
program a descriptor, enable bus mastering or the controller, ring a doorbell,
or interpret a response; the FIFO, DMA stream and ownership issues remain
unresolved. A host test checks exact command bytes and DMA-window boundaries,
and the diagnostic object compiles with the header. It has not been run on
hardware, and no storage command has been sent.

`j71s-identify-preflight.patch` integrates the preparation helper into the
one-shot diagnostic after its endpoint and MSI checks. It allocates the admin
queues and response buffer using the endpoint's provisional bounded DART window,
checks their layout, then frees them before the existing TCB initialization
experiment. If preparation fails, the TCB experiment is skipped. A combined
kernel containing the earlier one-cell window, FIFO one-shot changes and this
preflight compiled successfully. It has not been booted, and this preflight does
not send a command or prove physical DMA; it only prepares the specific buffers
needed by a later controller test. The device-derived window fragment remains
private and must be supplied separately.

A private DFU image for the combined preflight was assembled locally by
verifying and retaining the loader, one-CPU boot arguments, device tree and
initramfs from the previously booted bounded-window image, then replacing the
compressed kernel with the newly built combined diagnostic. The rebuilt image
and every component were hashed and rechecked, including a decompression check
of the kernel. This establishes package consistency, not boot or hardware
behavior. The image retains the one-shot test's kexec lockdown; a physical
restart is required after the currently running one-shot diagnostic before
booting it, and another restart would be required after a successful TCB arm.

`driver-patch/j71s-identify-once.h` is an unconnected experimental sequence
for one Identify Controller request. It checks the exact command and descriptor,
queue state, candidate scratch configuration, controller capabilities, PCI
state, kexec lock and an explicit caller-supplied ownership condition. It then
marks the preparation armed before writing queue registers, requests PCI bus
mastering, enables the controller, submits the command, and polls the first
completion. It deliberately does not disable the device, retire translations or
free memory; buffers must remain retained until physical reset on every path
after arming. The preparation release function now rejects an armed allocation.

The helper compiled in the ARM64 diagnostic build, and a fake controller test
exercises guard rejection, bus-master failure after arming, completion, and
command timeout. It is not wired into probe and has not been run on the iPad.
The caller's ownership flag is not proof: the actual host, DART mapping, SART,
TCB/SGL allocation, lifetime and PCI write-policy integration remain unfinished,
and physical DMA and invalidation are unverified. The currently packaged boot
image predates this helper and does not submit any storage command.

`driver-patch/j71s-identify-descriptor.h` links a prepared Identify response
buffer to a tag-zero TCB using the candidate device-to-memory direction. It
allocates a host SGL, checks its physical/identity mapping and address bounds,
and uses the shared descriptor builder to publish the count last. Once
published, the SGL and response buffer must be retained until physical reset;
the preparation context rejects cleanup or reuse after descriptor publication.
The one-shot command helper now requires that published state. The diagnostic
object compiled, and the descriptor-builder, command and simulated-controller
tests passed. This helper has not been connected to an initialized retained
TCB or executed on the iPad; it does not prove physical translation, DMA, or
safe invalidation. The prepared DFU image predates this change.

`j71s-identify-descriptor-probe.patch` is a follow-on to the FIFO one-shot and
Identify preflight patches. It keeps the prepared endpoint queues and response
buffer, exposes the retained TCB only when its init poll succeeded with its
buffers unchanged, and prepares the candidate tag-zero Identify descriptor
while the controller stays disabled. If descriptor preparation does not
publish, the endpoint buffers are freed before controller activation; after
publication, they and the host SGL remain retained. It requires the existing
Identify and descriptor headers to be included by the diagnostic source. The
object compiles and the related software tests pass, but the integration has
not been booted or run on physical hardware. A clear init poll does not prove
that the NVMMU fetched its tables, and publishing the descriptor does not prove
DMA, controller initialization, invalidation, or successful storage access.

`driver-patch/j71s-identify-scratch.h` is an unconnected candidate for setting
up the retained 14 MiB no-map scratch reservation and SART window for a later
Identify attempt. It validates the reservation and controller-disabled state,
zeros the reserved memory, programs candidate values, and reads them back. It
retains the mapping from the first window write onward, including error paths;
there is deliberately no teardown. The diagnostic object compiles with the
header. A fake-MMIO test exercises initial guard failures, all seven register
write/readback failures and success, and verifies that memory remains retained
after the first write. The code has not been wired into probe or run on the
iPad. Earlier controller-disabled tests verified individual register readbacks,
not DMA through this window. The current DFU image does not include or execute
the new setup.

`j71s-identify-master-integration.patch` and
`driver-patch/j71s-identify-master-policy.h` add a default-disabled policy for
exactly one endpoint bus-master enable. The guard requires the experimental
caller to opt in, provide a published descriptor and retained/ready scratch,
mark the request armed, keep kexec locked, and write only the expected command
transition on the matching endpoint. A write attempt consumes the permission even
if PCI reports failure, because a failed write could have side effects. The
policy mock and diagnostic object compile passed. No code currently enables
the opt-in or invokes the Identify helper. Root-bridge forwarding, physical DMA,
resource ownership, and cleanup are not established, and the current boot
image predates this policy.

Linux's PCI core normally enables bus mastering on an upstream bridge while
enabling a device. The temporary J71s diagnostic sets only the root bridge's
memory-enable bit, so endpoint master enable alone may not permit DMA
forwarding. `driver-patch/j71s-identify-root-master.h` is an unconnected,
one-shot candidate for the root command transition, guarded by the retained
request and scratch state, controller-off and endpoint-master-off checks, and
kexec lockdown. It records an attempt before writing and refuses a retry after
an error. A fake-MMIO test covers guard rejection, a write with side effects,
and the expected transition; the diagnostic object compiled. It is not enabled
in the current image, has not been tested on the iPad, and does not establish
that the bridge bit or physical DMA routing behaves as expected on S8000.

`j71s-identify-coordinator-candidate.patch` connects the prepared descriptor,
reserved scratch, candidate bridge transition, endpoint bus-master policy and
one-shot Identify sequence under an explicit `orchard,identify-once` device-tree
opt-in. The opt-in is absent from the current image. The diagnostic's PCI remove
callback retains its private context once a descriptor or hardware setup has
been published. The combined diagnostic object compiles, and individual mock
suites cover the command, scratch, bridge and endpoint policies; they do not
exercise the integration or real hardware. In particular, retained callback data
does not by itself prove the PCI core, host, DART domain or power state cannot be
removed. The device tree, physical DMA stream, bridge semantics, controller and
NVMMU lifetime still require validation before the opt-in is used. No storage
command has been issued, and the prepared DFU image predates this coordinator.

The combined descriptor diagnostic was subsequently booted directly from DFU
on J71s. The endpoint's Linux DART map reported first/last matches, unmapping,
the candidate aperture and an IOVA in that window. The specific Identify
preparation returned 0 with the controller disabled; TCB initialization returned
from its poll with retained buffers, and the Identify descriptor preparation
returned 0 with `published=1` and the controller still disabled. Kexec loading
was disabled and the diagnostic remained bound. Battery reported 35% and
discharging. This validates the allocations and descriptor preparation on this
iPad, not a hardware translation, a DMA transfer, a completed invalidation or
an NVMe command. The one-shot resources require a physical restart before
another hardware boot.

`j71s-diagnostic-armed-host-hold.patch` addresses a lifetime gap in the local
one-shot diagnostic: its platform shutdown/remove callback could wake the
worker and trigger PCI bus, MSI-domain and DART cleanup after TCB initialization
was issued. The candidate latches the armed state before that MMIO write, rejects
another initialization, holds the worker instead of following the normal stop
path, and skips diagnostic PCI and platform cleanup after arming. The object
compiled and the related Identify/scratch simulations passed. It is an
experimental guard, not proof against all kernel shutdown, device removal,
power or hardware-reset paths. It has not been run on the iPad and does not
replace the need for a physical reset; the earlier descriptor preflight image
predates this fix.

The Identify response buffer's candidate physical page is now required to fit
entirely below the 36-bit limit used for the host TCB and scratch allocations,
in addition to the existing alignment and DART IOVA checks. The host-side
boundary test and the Identify, scratch, bridge and endpoint policy simulations
pass; the combined diagnostic object compiles. These are address and software
checks, not proof of the S8000 translation path.

A private, separate DFU candidate now contains the compiled one-shot
coordinator and an explicit `orchard,identify-once` property. A device-tree
comparison confirmed that property is the sole logical change from the
previously booted tree; component hashes and kernel decompression were checked.
Unlike the prior preflight image, this candidate is designed to enable the
controller and attempt one Identify command if its guards pass. It has not been
booted. The new coordinator simulation checks opt-in behavior, operation order
and helper failures, in addition to the individual mock tests. None of these
checks proves actual DMA isolation, storage safety, bridge forwarding, or the
NVMMU semantics. Physical reset of the existing one-shot session is required
before this candidate could be tested; results must not be described as an
installation.

The candidate Identify path now emits non-identifying stage markers before
scratch setup, bridge setup, queue handoff, endpoint master enable, controller
readiness and command submission, and on a completion. These markers are for
troubleshooting and do not prove hardware execution by themselves. The
one-shot and coordinator simulations pass; the modified code is not yet tested
on the iPad. `j71s-identify-stage-markers.patch` contains the probe-level markers.

`j71s-identify-log-delay.patch` delays only the opt-in Identify test from three
to fifteen seconds, allowing a host to attach the RAM serial log observer
before the candidate controller sequence begins. The normal diagnostic delay
is unchanged. `observe-j71s-identify-kmsg.sh` follows selected messages for a
bounded time and reports DART translation faults without printing their raw
addresses. A shortened observer was verified against the current J71s RAM
session and captured the Identify-preparation, TCB-init and descriptor messages.
The delayed Identify build compiled, but neither the delay nor log capture has
been validated during an actual storage command, and a hard hang can still
prevent output or leave only a partial host log.

The one-shot candidate now requires an initially zeroed Identify response
buffer. After a successful completion it reports only whether the buffer became
nonzero and whether its PCI vendor field matches the endpoint; it returns an
error for an empty response or mismatched vendor. The simulated controller test
covers both failure cases and a plausible response. These checks avoid treating
an untouched buffer as a valid response, but a matching field alone would still
not prove all returned Identify data or sustained storage operation. The
modified diagnostic object compiled and has not been run on hardware.

`test-j71s-identify-descriptor.py` now exercises the actual descriptor wrapper
and shared builder with mocked DMA allocation. It checks locked-state refusal,
allocation failure, invalid DMA addresses, failed scatterlist lookup, nonidentity
mappings, invalid payload pages, successful direction/count/page publication,
and refusal to reuse the published descriptor. This is a software failure-path
test; the physical preflight and unresolved hardware DMA limitations above
remain unchanged.

`j71s-identify-observer-gate.patch` adds a separate, default-false runtime
start parameter in addition to the Identify device-tree opt-in. The candidate
skips the command if that parameter is not set when the diagnostic reaches its
one-shot branch. `observe-and-start-j71s-identify.sh` opens `/dev/kmsg`, starts
its bounded filtered reader, then sets the parameter if available. On the
previous RAM diagnostic, a shortened version captured the earlier preflight
messages and reported the absent gate without requesting a command. The updated
coordinator simulation covers a false start parameter, and the kernel object
compiled. This reduces the chance of an unobserved test; it does not guarantee
log delivery, and any privileged process could set the parameter. The gate
and new observer have not yet been tested with physical storage DMA.

`j71s-identify-observer-wait.patch` changes the explicit Identify experiment
to wait up to 60 seconds for the runtime start signal after its descriptor
preflight, instead of checking the signal only once. If the signal does not
arrive, the command is skipped and the already-armed one-shot resources remain
held for physical reset. The actual bounded wait helper has host tests for an
immediate signal, delayed signal, timeout and null input. The diagnostic build
is being prepared with this candidate; the wait has not been exercised on the
iPad or with physical storage DMA.

The candidate scratch setup now cleans the zeroed write-back mapping to the
ARM64 point of coherency before programming the candidate SART window. The
reservation is `no-map`, so the implementation cleans the actual `memremap`
virtual address rather than assuming a linear physical mapping. The mock test
checks that the clean follows zeroing and precedes MMIO writes, including all
seven write-failure cases; the diagnostic object compiled. This addresses CPU
cache visibility in the candidate only. It does not demonstrate that the
storage hardware can access the scratch window or that S8000 is coherent.

The scratch candidate now reads the controller's requested scratch size and
alignment and rejects zero, oversized, non-power-of-two or misaligned requests.
It also requires the candidate init register to be zero and rechecks those
fields immediately before writing the SART window. A mock test covers invalid
size and alignment in addition to the prior failure paths, and the diagnostic
object compiled. Earlier J71s controller-disabled observations reported a
14 MiB request with 4 KiB alignment; these new runtime checks have not yet run
on the iPad or established physical DMA.

`j71s-identify-require-dart-map.patch` makes the candidate require a successful
endpoint software-mapping test and the expected provisional DMA aperture before
allocating Identify buffers or arming the translation-table experiment. It
rejects an out-of-window IOVA or mismatched aperture before looking up the
mapped addresses and still unmaps/frees the test page. The bounded mock test
covers these failures as well as mapping and cleanup failures, and the diagnostic
object compiled. Earlier J71s preflight reported these checks successful, but
passing them still does not prove physical DMA isolation or hardware routing.


The maintainer-guided distinct-TCR-lock diagnostic was booted from DFU on J71s.
Its endpoint software mapping and candidate aperture checks passed, Identify
buffer and descriptor preparation returned success, scratch and root setup
reached the candidate path, endpoint bus-master enable read back, and the NVMe
controller reported ready. The final captured marker was immediately before
the Identify submission-doorbell write. The USB diagnostic device disconnected
shortly afterward; the serial observer eventually timed out without a final
result. No completion, response, or DART fault was captured. This does not prove
that the doorbell write completed, that a command executed, or that physical DMA
was isolated; absence of a captured fault after the disconnect is not evidence
that none occurred. Resources were intended to remain retained until physical
reset. Preserve the partial log privately and inspect the device before any
further test; do not retry automatically.

After the first one-shot attempt lost USB immediately after the pre-doorbell
marker, the candidate now gives the observer a short scheduling window before
that write and logs a second marker if the CPU returns from it. The function
then gives the observer another short window before polling. The simulated test
checks both delays and the existing timeout and response paths, and the object
compiled. A returned MMIO write may still be posted; the second marker would
not prove command delivery or DMA. This adjustment has not been run on J71s.

A comparison after the lost-USB Identify attempt found two differences from the
related J71t ANS driver worth investigating before changing test behavior.
The J71t driver explicitly writes zero to its controller INIT register before
programming HMB; the J71s candidate checked a zero baseline but did not issue
that write. J71t also configures LTR/L1SS before controller enable. Three
candidate J71s LTR/L1SS values were previously written, read back and restored
with the controller disabled, but were not kept active during the failed
Identify attempt. J71t additionally checks host link and fault state around
endpoint MMIO. These are hypotheses and debugging leads, not evidence that any
one difference caused the disconnect or that S8003 semantics apply to S8000.

The candidate one-shot helper now maps the SoC-side port and checks its `0x88`
bit-0 link indicator before endpoint configuration/BAR reads, before each CSTS
poll, and immediately before the submission-doorbell write. If that indicator
is clear or reads all ones, it stops the one-shot path and retains any armed
resources. Earlier controller-disabled J71s diagnostics observed bit 0 rise
with the negotiated link; its meaning during active storage I/O remains a
hypothesis. The actual-function mock covers a down link before any endpoint
read, link loss after arming without another CSTS read, cleanup of the temporary
CPU mapping, and existing completion/failure cases. The diagnostic object
compiled. This check has not been run with physical storage DMA and cannot
prevent an endpoint access from stalling if the link drops after a check.

The host kernel's USB log records the J71s RAM diagnostic disconnecting after
the first Identify attempt. In the inspected 20-minute window it showed no
USB over-current, disabled-port or device-descriptor error for that sequence.
This is only host-side evidence; a normal disconnect message does not identify
whether the device reset, stalled, lost power, or was unplugged. The user later
reported that the iPad returned to iPadOS, but the host had not yet detected it
again. The device's screen and cable/battery state must be checked before the
next physical test.


A second J71s attempt used the link-check and additional doorbell markers. The
endpoint mapping preflight, buffer and descriptor preparation, scratch setup,
root setup, endpoint master enable and controller-ready stages were reported.
The last captured message was again the pre-doorbell `submitting-command`
marker; neither the subsequent host-link-up nor the doorbell-write-returned
marker appeared before the USB diagnostic connection disappeared. The user
reported a black screen. These observations may place the failure before or
around the doorbell path, but missing output does not prove where execution
stopped, whether a posted write reached hardware, or that no DMA occurred.
No completion, response, or fault was captured. Do not retry automatically;
inspect and physically restart the device first, and keep the raw log private.


After the second lost-USB attempt, the experimental one-shot helper gained an
explicit controller-only comparison mode selected by
`orchard,identify-no-doorbell`. Following controller-ready it checks the candidate
host-link indicator for ten seconds and does not write the submission doorbell.
`j71s-identify-no-doorbell-coordinator.patch` passes that device-tree property to
the helper. The actual-function mock verifies no doorbell write, a bounded
wait and link-loss handling; the coordinator mock verifies mode selection, and
the diagnostic object compiled. This is a diagnostic comparison, not working
storage. Enabling the controller can itself cause DMA even without a submitted
command; all one-shot resources remain retained until physical reset. A physical J71s run reached controller-ready and remained responsive for approximately 10.4 seconds through the observation period, with the host-link indicator up and no submission-doorbell write. The observer completed normally. No command completion or Identify response was expected or captured. This narrows the difference from the two earlier failed command-path runs, but does not prove where those runs stopped or that any DMA succeeded.


The next command-path candidate uses the same ten-second link observation after
controller-ready before proceeding toward the submission doorbell. This tests
whether a longer settling interval changes the behavior; it does not establish
the cause of the prior disconnects. Resources remain retained until a physical
reset. The actual-function mock covers the warmup and link loss before the
doorbell. This candidate has not yet been tested on the device.


A subsequent physical command-path test completed the approximately 10.4-second
warmup and logged `submitting-command`, after which the diagnostic USB connection
disappeared without the subsequent host-link or doorbell-return markers. No
completion or response was captured. The delay did not change the observed failure;
missing asynchronous log output cannot establish whether the write was executed
or whether DMA occurred. Preserve the private capture and physically reset before
any further diagnostic.


A new comparison candidate continues from the ten-second no-doorbell observation
through the same barrier, pre-submission marker, delay and host-link check as the
command path, then records `doorbell-skipped` instead of writing the doorbell.
This isolates more of the preceding path but still permits DMA from controller
enable. Mocks verify the skipped write and link-loss handling. A physical test
reached the pre-submission marker, host-link check and `doorbell-skipped`, then
returned successfully with no valid completion expected. The USB log remained
responsive long enough to capture those markers. This comparison narrows the
difference with command-path failures, but missing asynchronous markers in the
earlier runs cannot prove whether the write happened or whether DMA succeeded.


The next command candidate leaves one second after the pre-doorbell link-up
marker for the observer to deliver it, then rechecks the link before writing.
The actual-function mock verifies the extra guard and retained resources on
link loss. This improves observability only; it does not prevent a stall after
the final check or establish that the command path is safe or functional.


On the next physical command attempt, the observer captured the host-link-up
marker before the extra one-second delay, then the USB connection disappeared
without a doorbell-return marker or a completion. This establishes that the
first pre-doorbell check was reached, but not that the final recheck or doorbell
write occurred or that a command executed. The comparison with the no-doorbell
run is suggestive, not proof of a specific failing instruction. Preserve the
private capture and physically reset before further tests.


A further no-doorbell candidate matches the command path through the extra
one-second wait and final link recheck before skipping the write. The mock
covers both successful skip and link loss at the final check. A physical run
captured the pre-doorbell marker, waited approximately one second, and recorded
`doorbell-skipped` followed by a successful return with no completion expected.
This strengthens the comparison with the command-path disconnect, but does not
prove the earlier write was reached or that DMA succeeded. Controller enable may
still cause DMA and resources remain armed until physical reset.


The maintainer's `feature/j71t-integration` branch at `c51cd22a381b` documents
the S8003 initialization sequence and awaits its own physical device test. Its
PCI patch 0015 polls the port invalidate FIFO before NVMMU initialization and
explicitly writes zero to SART control before programming the scratch-page and
TCB addresses. The current J71s diagnostic checks that SART control is zero
before initialization but does not explicitly write zero there; its FIFO
experiment runs after initialization. These are concrete sequence differences
to investigate, not proof of a J71s defect or permission to assume S8003
register semantics on S8000. The previous command-failure captures do not
isolate either difference.


The one-shot initialization candidate now checks the proposed port FIFO empty
indicator before programming NVMMU addresses or issuing initialization, based on
the related S8003 sequence. A missing mapping, all-ones status or timeout stops
the test before those writes. The mock exercises the empty, nonempty and invalid
status cases and verifies no initialization writes on failure. The meaning of
this status bit on S8000 and any effect on storage remain unverified. The
observer includes the new pre-init result without exposing device identifiers.


For the first physical run of this guard, the prepared RAM image uses the
previously verified no-doorbell device tree. Its device-tree properties and
component hash were checked against the assembled image; the coordinator mock
also verified no-doorbell mode selection. This still enables the controller,
so it is not evidence that no DMA can occur. The physical run is pending.
