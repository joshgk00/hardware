# J71s USB NFS physical test record

This is a bring-up record, not an installation guide. It concerns an iPad 5
Wi-Fi J71s with the S8000 SoC. The root ran on a connected computer, not on
internal iPad storage. The tested NFS export and post-handoff rescue shell are
unauthenticated; this arrangement is for an isolated, trusted host only.

## Current status

The later upstream-based image has booted this J71s into an NFS-backed running
system. It enumerated touchscreen, audio, Bluetooth, light-sensor and video
devices; interactive touch and audible sound on this image remain unconfirmed.
Internal storage, Wi-Fi, charging and installation are not established. The
chronological entries below preserve what was known at each step; later entries
supersede earlier statements that a build or boot was pending.

## Inputs

- Kernel base: Orchard Linux `6831bc701a6ce059e71e5aaa9488c9195bea6927`,
  plus the local J71s display/touch and hardware overlays used by this
  experiment. The source tree was modified; the base commit alone is not a
  complete reproduction recipe. A private snapshot now preserves the tracked
  diff, eight untracked source files and the config; a reverse/apply round trip
  reconstructed all 29 changed files byte-for-byte. An incremental retry of a
  reconstructed build later succeeded but did not reproduce the booted binary
  byte-for-byte, as recorded below. The overlays need provenance and licensing
  review before publication. The touch/SmartIO starting point was patches 0003
  and 0004 from [hardware PR 6](https://github.com/OrchardLinux/hardware/pull/6)
  head `f764d95f70616adae483a97aaa7dae9f18cc8114`; later local changes include
  J71s matching and staged touch bring-up, plus battery-source work. These
  must be compared with the later upstream integration before reuse. Comparing
  the eight added source/binding files against those two original PR patches
  found seven byte-identical files. The local N1 driver adds a J71s compatible
  and forces stage 3 for J71s; that experiment-specific forced stage needs
  review before it can be proposed as supported behavior. The tree
  used for the patched build differs
  from the immediately preceding NFS build's tree in `f_ncm.c` by the two-line
  [proposed upstream NCM timer change](https://patchew.org/linux/20260727165441.1969927-1-flavra@baylibre.com/).
  Credit for that change belongs to its upstream author.
- Both compared builds used the same kernel config (SHA-256
  `2ca48f13f92d4779d79192cc8a2b23601c7a37784e1683a5665e6245f5041f71`),
  16 KiB pages, release `7.3.0-rc1`, and built-in NFSv4, USB NCM and ACM.
  The uncompressed baseline and patched kernels have SHA-256 respectively
  `fe1589c2d3af131682aad98dd93fd93d36f9b8b8a29a47dfba5f9153ee3cb70e` and
  `8008099424c156c76a9a4dfd08f2eadff9f494f8d327d89473302f25aab4f14d`.
- The same staged RAM startup, device tree and root were retained when the
  patched image was assembled. The prepared root is an isolated copy of an
  existing J71b Omarchy image, with a J71s-specific handoff guard and J71b
  charging lease disabled. It is not a published J71s image.
- Host server: `neilpang/nfsd` commit
  `b9ac075cefb301707aae08105c523a1a387f0adb`, rootless user namespace with
  root UID and GID mapped, NFSv4.0/TCP on the dedicated USB interface.
  The boot retained the explicit bring-up-only rescue option.

## Observations

The unpatched boot passed read-only identity validation and entered systemd on
an NFS root, but repeatedly logged that the server stopped responding and later
recovered. The host saw packet loss; the server reported expired NFS leases and
systemd reported a journal watchdog failure. No usable desktop was confirmed.

The patched boot passed the same root validation and reached systemd `running`
with no failed units at the check. The user saw the Omarchy desktop, opened the
on-screen keyboard, filtered the Super menu, opened the terminal and typed in
it. The tablet user wrote, synced and read a 16 MiB temporary file; the host
confirmed matching SHA-256 and UID/GID 1000, and the user removed the probe.
Several short ping samples totaling over 100 checks had no observed loss, and
no NFS timeout lines appeared in the retained kernel log at the checks.

This is one boot per condition, not a controlled repeated comparison. It does
not prove that the NCM patch alone caused the improvement, qualify the server,
or establish long-term stability. It does not establish working S8000 PCIe,
internal storage, Wi-Fi, charging or an installer. Raw device logs, firmware,
per-device identity and assembled images are intentionally kept private.

## Upstream integration investigation, in chronological order

Hardware main `0cfb171` no longer uses the separate `apple_n1` driver: its
[integrated J71t touchscreen patch](https://github.com/OrchardLinux/hardware/blob/0cfb17118261ac37e1d5019d45c63237fb550c73/kernel/patches/drivers/input/0009-Input-apple_z2-Add-iPad-5-J71t-touchscreen-support.patch)
folds the protocol into `apple_z2` and explicitly omits the original stage
parameters. The J71s device tree includes the shared iPad 5 touch node using
the J71t compatible, and its firmware recipe builds `j71s-fwstart.z2fw`. The
matching shared driver's expected 40-by-30 sensor and 14745-by-19657 surface
agree with the earlier J71s stage-2 discovery. Orchard's m1n1 patch forwards
the unit calibration to the driver. These facts make an upstream-based J71s
RAM touch boot the next integration comparison, not proof it will work: the
upstream kernel, its J71s tree, m1n1 handoff, firmware and this exact device
had not yet been tested together at that point. The later physical boot is
recorded below.

The previously extracted J71s mtprops from the installed iPadOS 16.7.16 build matched the upstream recipe’s pinned input SHA-256. Orchard CLI `a2dd45f` converted it using the J71s recipe parameters, and the generated Z2FW matched the upstream expected SHA-256. The resulting firmware remains private. This validates the input and conversion only; it does not prove calibration handoff or touch operation with the integrated driver.

Using the current Orchard CLI, the S8000 SmartIO firmware was also extracted from the previously saved iPadOS 16.7.16 kernel cache; its digest matched the J71s upstream recipe. The firmware is kept private. This verifies a second test input, not SmartIO operation with an upstream-built kernel.

For the upstream comparison, the pinned Linux source `cee9395acd8043be0644b25c34bfa86623f2b935` was fetched, and all 358 ordered Orchard hardware `0cfb171` J71s patches passed `git apply --check` and applied to a separate tree. The proposed NCM timer patch also applied cleanly afterward. The upstream config makes NFS, SmartIO and the integrated touch driver modules, so the matching modules and firmware must be staged before physical testing. This source preparation is not a kernel build or device test.

On 2026-10-30, a check of [Linux mainline's NCM source](https://raw.githubusercontent.com/torvalds/linux/master/drivers/usb/gadget/function/f_ncm.c) still showed the unchecked transmit return in `ncm_tx_timeout`. A [separate proposal by Cosmin Tanislav](https://lists.openwall.net/linux-kernel/2026/08/17/1825) addresses the same stalled transmit case and advances the timer with `hrtimer_forward_now` before returning `HRTIMER_RESTART`; the Lavra patch in our current physical test does not include that adjustment. Lavra [followed up on the original proposal on October 22](https://lkml.iu.edu/2610.2/15904.html). These are proposals, not evidence that either patch was merged or that either behavior was exercised in our test. Review the timer semantics and compare the alternatives before choosing a patch for another build; the running device was not modified.

The [mainline hrtimer implementation](https://raw.githubusercontent.com/torvalds/linux/master/kernel/time/hrtimer.c) re-enqueues a timer on `HRTIMER_RESTART` without itself advancing its expiration, and its queue runner processes timers whose expiration has passed. This suggests the Lavra variant could retry immediately and repeatedly while transmission remains busy, unless some other concurrent path advances or queues the timer. Tanislav's proposal explicitly advances it by the NCM timeout before restarting. This is a source-level concern, not an observed hang or proof of the behavior on the tested kernel. Before another physical test, check the pinned kernel's corresponding implementation and review concurrent timer operations; test the busy path specifically rather than inferring it from ordinary NFS uptime.

Follow-up: the exact base commit `cee9395acd8043be0644b25c34bfa86623f2b935` has the same re-enqueue and expired-timer loop behavior. Its NCM timeout is 300,000 ns, with timer start, try-cancel during packaging, and cancel on teardown; concurrent activity still needs review. The publicly posted Tanislav patch passed `git apply --check` against a clean copy of that commit's `f_ncm.c`. This checks patch compatibility with the base file only, not the fully patched build, compilation, concurrency safety, or physical behavior. It was not installed in the running kernel.

At that base revision, `eth_start_xmit` returns `NETDEV_TX_BUSY` both for a suspended USB port and for an empty transmit-request list, before calling NCM's wrapping function. The wrapping function runs under the Ethernet device lock, but the timer callback releases the transmit function's locks before the proposed `hrtimer_forward_now` call. The timer can also be started by the wrapping path; `hrtimer_forward` warns if the timer is already queued when its expiry is due. Whether an actual interleaving can reach that warning or otherwise mishandle a concurrent start has not been established. The next review/test should cover suspend and disconnect as well as request exhaustion, and explicitly exercise concurrent packet arrivals, timer retry and teardown. No production-safety conclusion follows from patch applicability.

One candidate interleaving for that test is: the timer's transmit sees an empty request list and returns busy; a request then becomes available; a concurrent transmit fills and packages the pending NCM frame, starts a new frame and restarts its timer; the original callback reaches `hrtimer_forward_now`. The pinned `hrtimer_forward` first returns without a warning if the new expiry is still in the future, and only checks the queued warning after that. Whether the timing, locking and timer internals permit the problematic case remains unproven. A targeted test must observe this scheduling and timer state directly rather than treating ordinary concurrent traffic as proof.

For off-device investigation, a separate ARM virtual-kernel build was started from the alternative NCM source with `dummy_hcd`, host CDC NCM, kprobes and function tracing enabled, using the previously used VM console configuration. A small temporary initramfs to create an NCM gadget was prepared. The first configuration was stopped after review found it lacked the VM console; the corrected build is in progress. No VM boot, traffic, retry injection or race test has yet been performed, and a software dummy controller cannot establish physical DWC2 behavior.

A preliminary VM boot with the older kernel (which lacks `dummy_hcd`) exposed an incorrect test assumption: the script selected the `sit0` tunnel as a USB host interface. The script now selects only interfaces bound to `cdc_ncm` and stops when no UDC is available. A second boot with the older kernel reached the expected missing-controller guard without claiming a network test passed. QEMU's `max` CPU model booted this 16 KiB-page kernel; a `cortex-a57` attempt produced no console output before its timeout, with cause not established. The new test kernel was still compiling during these checks.

The virtual config also builds the legacy `g_multi` gadget in; it could claim a newly available dummy controller before the configfs NCM test. The prior VM kernel has the `multi_driver_init` symbol. In isolated no-UDC VM boots, the expected `g_multi` no-controller message appeared normally and was absent with the command-line option `initcall_blacklist=multi_driver_init`; the missing-controller guard still ran. Use that option for the forthcoming VM only, and verify actual NCM ownership when the new kernel boots. This check does not establish behavior with the dummy controller present.

As a separate smoke test while the new kernel built, `dummy_hcd`, `mii`, `usbnet`, `cdc_ether` and `cdc_ncm` were compiled as external modules against the older VM kernel. The first build lacked the MII dependency and failed modpost; adding it produced all five modules. With the legacy gadget initcall blacklisted, a QEMU boot loaded them, created `dummy_udc.0` and two USB network interfaces, moved the host-side interface into another network namespace, and passed three pings without loss. The VM correctly reported the fault hook absent. These external modules tainted the VM kernel; this validates the isolated test harness on the older kernel, not the alternative NCM patch, forced busy path or physical hardware.

The VM configuration has kprobe events and tracing, but does not enable the kernel function-error-injection facility; neither `eth_start_xmit` nor `ncm_tx_timeout` is marked for that facility in the checked USB gadget source. Therefore the initial VM connectivity smoke test cannot force the busy return or validate retry behavior. A separate, explicitly test-only mechanism and evidence that the targeted branch was reached will be needed; no injection hook was added to the physical kernel.

`ncm-vm-force-busy.patch` is a VM-only candidate that replaces one timer callback's transmit result with `NETDEV_TX_BUSY` after a test parameter is armed. The modified NCM object compiled in a separate source/output copy, and the patch applies to the alternative NCM source; it has not been linked or executed. This synthetic return can exercise the retry branch, but does not reproduce a genuinely exhausted request list, suspended port or concurrent timer race. Never include the hook in a physical-device image or production patch.

To test sooner, a separate copy of the older `6831bc701a6ce059e71e5aaa9488c9195bea6927` VM kernel source was patched with the Tanislav retry and VM-only hook, then incrementally linked with the old VM config and release. With the five external USB modules and dummy controller, one QEMU boot passed three baseline pings, consumed the one-shot busy hook, and passed three more pings with no loss. The retained VM log had no matches for `WARNING:`, `BUG:`, `soft lockup` or `hrtimer`. This demonstrates one synthetic busy return followed by successful traffic in that older virtual environment; it does not prove which packet encountered the injected return, the timing of retry, genuine request exhaustion, suspend/disconnect safety, concurrency, or physical DWC2 behavior. The newer upstream-based VM build remained separate and running.

A second instrumented build added a read-only callback counter. After a three-ping warmup, the test armed the one-shot busy hook and sent one ping. The ping succeeded, the hook cleared, and the callback count increased by two. This is consistent with a busy callback followed by another callback, but without a per-callback trace it cannot prove their exact order, timing or traffic association. It still simulates the return rather than exhausting real USB requests, and does not validate the separate physical candidate.

A third VM-only instrumented build recorded callback sequence numbers at the forced busy return and the next callback. In one run the busy marker was 11 and the next marker 12; the one-ping check succeeded and the one-shot hook cleared. This establishes the order of those markers in that run, not a retry interval, packet attribution or behavior under real USB request exhaustion or concurrent teardown. The markers are test instrumentation, not part of the physical kernel or the upstream proposal.

Adding monotonic timestamp markers to the same VM-only hook yielded one 260,848 ns interval between the forced-busy marker and the next callback; the markers were consecutive and the one-ping check succeeded. This is one instrumented QEMU sample, not a timing guarantee. `hrtimer_forward_now` advances the previous expiry in timeout-sized increments to a future point, so the measured interval from the marker need not equal exactly 300,000 ns. Real controller congestion, packet attribution and concurrency remain untested.

A comparison VM build used the same config and instrumentation but omitted `hrtimer_forward_now`, matching the relevant retry behavior of the Lavra proposal used in the physical boot. In one run the forced-busy and next markers were consecutive, 58,240 ns apart, and the one-ping check succeeded. The two source files differed only by the forwarding call. The 58,240 ns and 260,848 ns readings are single samples under QEMU, not a statistical comparison or proof of real-device timing; forcing busy once also cannot establish what happens during sustained request exhaustion.

The VM-only hook was then extended to return busy four times. In one run of each timer variant, the hook recorded four forced busy callbacks, the callback count increased by five, and the single test ping succeeded. The first busy-to-next-callback marker intervals were 262,096 ns with forwarding and 48,208 ns without it. This bounds the simulation to four artificial returns and checks only the first interval; it neither exhausts actual USB requests nor establishes sustained behavior, CPU cost, concurrency safety or physical-device performance. The injection counter is for a single VM test instance, not a production interface.

With the same hook configured for 100 consecutive synthetic busy returns, one run of each variant recorded 100 forced callbacks, a callback-count increase of 101 and a successful single ping. The ping reported 34.086 ms with forwarding and 4.245 ms without it; the first marker intervals were 298,720 ns and 83,632 ns respectively. These are single QEMU runs, not throughput or CPU-cost measurements, and the forced returns do not model real request exhaustion. The shorter time without forwarding is consistent with immediate retries, but this does not establish safety under sustained congestion or on hardware.

Three further isolated runs per variant each consumed all 100 forced returns, recorded 101 callbacks and completed the single ping. First-marker intervals were 209,904, 179,648 and 290,256 ns with forwarding, versus 80,528, 63,840 and 72,032 ns without. This small non-randomized QEMU sample supports the observed difference in the synthetic setup, but does not measure actual USB request exhaustion, CPU starvation, race safety or the iPad's hardware.

An isolated copy of the actual Orchard-patched source was then changed from the Lavra variant to the published Tanislav patch; `git apply --check` and application succeeded. Using the existing local kernel toolchain container (`LLVM=-19`, `ARCH=arm64`), `make -j1 drivers/usb/gadget/function/f_ncm.o` succeeded against a copied output tree whose `.config` SHA-256 matched the running build's config. This is a single-object compile, not a full kernel build, linked image, concurrency test, or boot. The first attempt with the host compiler failed because the host lacked the requested linker; the container retry produced the object. Original build artifacts and the running device were left unchanged.

The isolated output was subsequently linked successfully with `make O=/work/output ARCH=arm64 LLVM=-19 LOCALVERSION=-orchard-apple-16k -j1 Image`. The resulting Image has SHA-256 `6e22877ac3526f0eb61552236cddade96631c2ed0adab1ae2f1fc3a57aa2a8d4`, release `7.3.0-rc1-orchard-apple-16k`, and a `.config` hash matching the current physical build. The first link without the explicit local version produced `7.3.0-rc1+`; that image was superseded. This incremental build reused copied prior output, so it is not a clean rebuild or proof that the existing modules are compatible. The image has not been packaged into a boot payload or booted. Test preparation must verify module compatibility and runtime behavior before use.

The same isolated tree subsequently passed `make -j1 modules` with that release and toolchain. Orchard's staging tool processed 69 modules; all 69 staged `.ko` files match the currently booted build's staged module files byte-for-byte, and the touch module's vermagic names the expected release. A separate private kernel directory now contains those modules, the earlier staged J71s DTB, release file and gzip-compressed alternative Image; decompressing the latter reproduced the Image hash above. This is stronger build-artifact evidence, not proof of runtime loading or a complete boot payload. Device-tree selection, root/runtime receipts, loader assembly and busy-path safety still require validation before a physical test; the live root and boot image were not changed.

After the alternative `modules` build regenerated `Module.symvers`, its 13,157 exported-symbol entries matched the earlier build as sets. Both builds disable `CONFIG_MODVERSIONS`, so this does not validate per-symbol ABI checksums or establish runtime module compatibility; the copied build output also makes this an incremental comparison.

An alternative private NFS payload was assembled with the original upstream loader, boot arguments, J71s DTB and initramfs after each input's hash matched the physically booted payload receipt. Its component receipt was checked against the output bytes, including offsets, lengths, hashes and m1n1 initramfs framing; all components except the deliberately replaced compressed kernel match the previous payload. This is an offline packaging check, not a boot, concurrency or fault-injection test. The old initramfs is reused with modules whose staged counterparts matched byte-for-byte; its existing root and network settings must be revalidated against the live environment before any later boot. Do not switch the active NFS export while the current iPad session is using it.

The original NFS runtime receipt identifies the original kernel image, so it cannot serve as a receipt for the alternative kernel. The upstream staging tool was rerun in a separate private directory with the alternative kernel and the same root identity, network parameters and BusyBox. All 14 staged runtime files and the five selected NFS module hashes matched the old runtime; its new receipt identifies the alternative compressed kernel rather than the original. Thus reusing the byte-identical initramfs has an independently regenerated staging receipt, but the full root/network preflight and physical boot remain outstanding. No live export was changed.

At a later host preflight, the alternative payload's kernel hash matched its new runtime receipt, the root identity matched the current private root receipt, and the staged network settings specified the expected NCM function, manual handoff, server and port. The existing rootless NFS container was running, the dedicated USB interface had the expected IPv4 address, and the server port was listening on that address. This is a snapshot for the current session, not authorization to interrupt it or a guarantee that these conditions will still hold after a physical restart. Recheck immediately before any boot.

A separate private launcher was prepared for the alternative payload, selection receipt and log, leaving the active boot's files untouched. A syntax check passed and an AST comparison after normalizing those three paths and the image hash matched the launcher used for the upstream physical boot. This checks the intended textual differences only; the new launcher has not been executed. It still requires a freshly identified device in DFU and a new selection receipt, plus the preceding network/root and battery checks.

At 5,867 seconds uptime on the current Lavra-patched upstream boot, systemd still reported `running`, battery reported 36%, and the retained kernel log had zero case-insensitive matches for `soft lockup`, `hard lockup`, `hrtimer`, `watchdog`, and `nfs: server`. This is a point-in-time scan of retained logs, not proof that the busy retry branch was reached, that no earlier messages were lost, or that either proposed fix is safe. Save the equivalent measurements for the alternative boot and use a separately designed controlled congestion test before drawing comparisons.

At 6,363 seconds uptime, systemd again reported `running` with zero failed units; battery was 35%. The same retained-log search still found no matches for those terms, and a search for `iommu fault` also found none. PCIe is disabled in this boot, so the latter is not a PCIe DMA or storage test. These are sampled results with the same log-retention limits.

With the charging node disabled and the iPad connected to the computer, a later battery-gauge sample reported 35%, `Discharging`, 3.767 V and -573 mA. This is net battery current reported by the gauge, not measured USB-port current, a charging grant, or a runtime forecast. The upstream [J71t integration notes](https://github.com/OrchardLinux/hardware/blob/0cfb17118261ac37e1d5019d45c63237fb550c73/docs/integration/j71t.md) describe source-specific current grants and remaining J71t charging questions; their [input-limit recovery patch](https://github.com/OrchardLinux/hardware/blob/0cfb17118261ac37e1d5019d45c63237fb550c73/kernel/patches/drivers/power/0013-power-supply-apple_tristar_charger-Restore-the-input.patch) describes a PMIC reverting to 100 mA on J71t. Neither establishes J71s charging or the computer's source capability. A J71s test still needs verified hardware equivalence, source identification and withdrawal, pack safety, and monitored measurements before enabling this node.

A subsequent read-only gauge sample reported 35%, discharging, temperature 28.4 °C, health `Good` and battery present. The kernel ABI documents the temperature unit as tenths of a degree Celsius. These are driver-reported instantaneous values, not an independent temperature measurement or evidence that charging is safe.

For the integration note's specific question about the PMU event line, the private J71s ADT has an eight-byte PMU interrupt record whose first little-endian word is 76; its `interrupt-parent` phandle resolves to the SoC GPIO node. This agrees with the upstream shared iPad 5 tree's candidate GPIO number and parent. The second ADT word, interrupt polarity and runtime delivery were not decoded or tested, so this is not proof that the full Linux interrupt specifier or charger withdrawal behavior is correct. Raw ADT data remains private.

`check-pmu-interrupt.py` repeats that limited comparison using the unified Orchard ADT parser, printing only match results. Three synthetic tests cover the match, malformed or wrong interrupt record, ambiguous parent reference and duplicate PMU path; the private J71s input matched both checks. The helper is an offline comparison, not a charging test.

The private J71s ADT also contains PMU and Tristar nodes under `i2c0`; their 16-byte `reg` properties have first little-endian words `0x3c` and `0x1a` respectively, matching the candidate I2C unit addresses in the shared upstream iPad 5 tree. This comparison does not decode the remaining words, identify the precise chip revisions, validate register semantics, or demonstrate charging.

The PMU comparison helper now checks both address records as well as the interrupt number and parent. Four synthetic test cases passed, including wrong first words and malformed address lengths; the saved J71s ADT matched all four comparisons. The additional checks retain the same limitations as the raw-field comparison above.

On the current physical boot, sysfs lists an I2C device with the upstream `apple,angel-pmic` and `apple,i2c-pmic` compatibles bound to `simple-mfd-i2c`. It also lists the `nxp,cbtl1610` I2C device without a separate I2C driver binding. The shared charging driver's source looks up the Tristar I2C device through its phandle, so the lack of a separate binding is not itself proof of a fault. The charging node remains disabled; enumeration and a PMIC binding do not verify charger operation, event delivery or safe current handling.

The PMIC GPIO platform child also appears in sysfs and is bound to `apple-d2365-pmic-gpio` on this boot. A simple search of GPIO class labels for `pmic` or `d2365` returned no matching label, so no GPIO-chip or interrupt-domain conclusion is drawn from that search. Driver binding is not proof that GPIO interrupt delivery or charger withdrawal works.

The live PMIC GPIO device tree has the `interrupt-controller` property. In the source used for this build, the D2365 match supplies event-controller data, and successful GPIO probe follows successful event-domain creation and parent threaded-IRQ request. Together with the observed binding this supports successful software setup of that path on this boot; it does not show that a physical interrupt was delivered, that mask writes had their intended hardware effect, or that source withdrawal is safe. No PMIC registers were accessed by this follow-up check.

The running kernel's `/proc/interrupts` includes one entry named for the PMIC GPIO platform device, on Apple GPIO 76 with a level-triggered handler; its two CPU counters were both zero at the sampled time. This provides a baseline for a future observed event, not a polarity measurement or evidence of a fault: the charger is disabled and this check did not deliberately trigger an event.

An Orchard m1n1 loader for the upstream comparison was built from pinned source `c9ef56f7356e93e6f6cac116c529d31c277ef6a6` with all 52 hardware `0cfb171` loader patches. Its source locates the `touchscreen0` alias and forwards the unit’s `multi-touch-calibration` from the live ADT to `apple,z2-cal-blob`; the shared iPad 5 tree supplies that alias. The built loader has not been booted on J71s, so calibration handoff remains unverified in hardware.

A separate upstream-test root was extracted from the hash-verified original Omarchy archive with root and tablet ownership checked. It has a fresh private J71s receipt for kernel `7.3.0-rc1-orchard-apple-16k`, the existing guarded test-root preparation, and the hash-verified J71s touch and S8000 SmartIO firmware. Matching kernel modules and a staged RAM startup are still required; the new root has not been booted. The currently running root was not modified.

Before staging the upstream test, all 13 upstream hardware `0cfb171` NFS runtime unit tests passed locally against that checkout. This covers the runtime fixtures, not the as-yet-unbuilt J71s kernel, real module set or physical boot.

The upstream shared iPad 5 device tree includes a Lightning charging node, while J71s charging is not yet qualified. The test-only `j71s-upstream-touch-no-charge.dtso` disables that node; it compiled and applied to a synthetic tree without removing its touch node. The override still needs to be applied to and verified against the actual built J71s DTB; it is not a charging-support change or a complete device safety assessment.

The upstream-patched J71s device-tree source was also compiled independently of the still-running kernel build. Applying the test-only charging override preserved `apple,j71s`, disabled the charging node, and preserved the touch compatible, J71s firmware name and `touchscreen0` alias. `dtc` reported simple-bus and interrupt-provider warnings; this preliminary tree must be compared with the build-produced DTB and validated before use. It does not verify runtime calibration, touch, charging, or all other devices.

A separate preflight compile of the upstream J71t tree produced the same five warning types, node paths and messages as J71s: one simple-bus unit-address warning and four interrupt-provider address-cell warnings. They are shared by these two preflight builds rather than introduced by the charging override. This comparison does not establish that the warnings are harmless or replace device-tree schema validation.

The tested N1 device tree and the upstream J71s preflight tree both set the touchscreen SPI maximum to 12,048,192 Hz and request inverted Y. The tested tree specifies 5 microseconds of chip-select setup and 10 microseconds of hold; upstream puts 10 microseconds for each in the integrated J71t driver rather than in the tree. Actual controller/core timing must be checked when the upstream driver is tested; this source comparison does not prove either timing caused or prevents a problem. The driver interfaces and firmware formats also differ.

The upstream NFS staging code accepted the separate root receipt and intended kernel release, the previously checked static ARM BusyBox, and the isolated USB subnet/export parameters. Its resolved kernel config enables the firmware loader while building NFS, SmartIO and touch as modules; the root’s `/lib` points to `/usr/lib`, where the firmware inputs were staged. This is an offline preflight only; matching modules, module loading and the physical boot remain unverified.

During the same running desktop session, the tablet user wrote and synced 4 MiB of random data. Host and tablet SHA-256 values matched, host ownership and mode were 1000:1000 and 0600, and the probe was removed from both views. This complements the prior zero-filled write; it does not establish long-term filesystem reliability.

At approximately 45 minutes of kernel uptime in the patched boot, the rescue console reported systemd `running`, battery 62%, and no NFS server timeout lines in the retained kernel log. The ring buffer may not retain all earlier messages; this sample alone does not establish uninterrupted operation for the whole interval.

The first upstream build used an older local container missing the ARM userspace cross-link dependencies; `olddefconfig` dropped `CONFIG_CC_CAN_LINK`, so that build was stopped and its output is not used. A separate container built from hardware `0cfb171` installed the prescribed cross packages, successfully linked an AArch64 userspace probe, and resolved the upstream config byte-for-byte. A fresh build using that corrected container and a new output directory is in progress. This is not yet a completed or physically tested build.

A read-only inventory in the patched desktop boot showed one DRM card, no entries under the Bluetooth or IEEE 802.11 device classes, and no NVMe block device; the battery reported discharging at 62%. These are observations of this experimental kernel and boot, not proof that the physical radios or storage are absent or permanently unsupported.

The J71s Bluetooth HCD stream was extracted from BlueTool in the locally saved iPadOS 16.7.16 archive with Orchard CLI `a2dd45f`; its digest matches the upstream J71s recipe, and it was installed only into the private upstream test root. The shared tree enables a Bluetooth UART node, and the resolved upstream config enables the Broadcom UART support as part of the HCI UART module. The kernel driver selects its board-specific HCD using the root compatible (`apple,j71s`). Bluetooth has not been enumerated, paired or otherwise tested with this kernel on J71s.

Twelve J71s Wi-Fi firmware inputs were extracted from the locally saved iPadOS 16.7.16 archive; each matched both the input and output SHA-256 in the upstream J71s recipe. They were installed only into the separate private upstream test root. This prepares firmware for future PCIe testing; S8000 PCIe and Wi-Fi are not working or validated.

The video-decoder firmware extracted from the saved iPadOS kernel cache matched Orchard’s pinned J71s recipe and was staged only in the separate private test root. This prepares a firmware input; video decoding has not been tested or established.

A final hash audit checked all 16 firmware outputs in the upstream J71s recipe against their files in the private test root: all matched, with none missing. This is input validation only; it does not establish that any hardware driver loads or functions.

The separate clean reconstruction build stopped when compiler processes were killed with exit 137. The exact cause was not confirmed from the checked system logs; its resolved config still matched the saved config. The build was restarted incrementally with one low-priority worker in the same isolated output directory. This retry remains incomplete and does not change the running iPad or the corrected upstream build.

The upstream m1n1 ADT lookup checks `/arm-io/<function>` and one level below each `/arm-io` child. The earlier private J71s ADT inspection found the touch node at `/arm-io/spi3/multi-touch`, which fits that lookup, and the prior stage-2 test used a nonblank 1024-byte calibration property from this device. This is a source-and-input compatibility check; it does not prove m1n1 will forward the property on the next physical boot.

Source review of the upstream DWC2 VBUS-draw work found that it returns when the named power-supply provider is absent. This is consistent with the test-only disabled charging node not requiring a provider for that callback, but has not been runtime-tested on J71s and does not prove USB or charging behavior.

A further read-only inventory of the running experimental boot found a backlight class device, but no entries in the sound class or IIO sensor directory; the battery reported discharging at 59%. Brightness control, sound and sensors were not functionally tested by this inventory.

The user confirmed that both touch and on-screen keyboard input work in the running desktop session. This is a functional observation of the current experimental image, not yet of the upstream-based candidate.

The upstream shared iPad 5 device tree describes a CS42L81 audio codec, an S8000 MCA interface and a TSL2581-compatible ambient light sensor. The corrected upstream build configuration enables the corresponding codec, MCA, simple-audio-card and TSL2583 drivers as modules. These source and configuration checks identify candidates for the next hardware inventory; they do not demonstrate successful probing, sound output or light sensing on J71s.

The corrected kernel build produced its J71s DTB while compilation was still in progress. Applying the test-only no-charge overlay to that built DTB produced SHA-256 `ce60928232e09f177baed6fcc947e6a6cbc534058d33f74c184e265ae155c729`, byte-for-byte matching the separately compiled preflight DTB. The kernel build and physical validation are still pending.

The reconstructed experimental kernel build completed successfully on its incremental single-worker retry. Its uncompressed Image differs from the decompressed kernel in the physical boot image. Their embedded build banners include different container hostnames, which alone prevents byte-for-byte identity; other differences have not been ruled out. This demonstrates that the preserved source and configuration can build, but does not establish a reproducible binary or validate the rebuilt kernel on hardware.

The upstream CLI RAM build test suite passed all 38 tests against the checked-out hardware tree. These use synthetic inputs and exercise the real initramfs packer and image assembler with mocked USB; they do not validate the forthcoming J71s image or a physical boot.

As a staging preflight, the upstream module installer processed all 41 modules from the completed experimental rebuild and generated a populated `modules.dep` with 41 entries. This checks the local staging toolchain on real build output; the separate upstream candidate still needs its own modules staged and tested.

The corrected upstream build later stopped with exit 2 after a compiler for `lib/sys_info.o` was killed with exit 137. A check of recent kernel logs did not identify an out-of-memory event, so the cause is not established. The same output directory and fixed build metadata were retained and an incremental single-worker retry was started; its result remains pending. The running iPad was not rebooted.

The resolved upstream configuration enables gzip initramfs unpacking, devtmpfs, IPv4, DWC2 dual-role USB, configfs, and the ACM and NCM gadget functions built in. NFS and NFSv4 are modules and must be staged with their dependencies in the RAM runtime. This verifies required configuration choices only; it is not a boot or connectivity result.

The upstream shared iPad 5 tree also describes a UART HDQ battery fuel gauge, and the resolved configuration builds the UART one-wire and BQ27xxx HDQ drivers in. The separate test override disables the Lightning charger node, not the fuel-gauge node. Battery reporting and charging behavior under the upstream candidate still require physical validation.

During the prolonged experimental desktop session, a later attempt to run a read-only serial check timed out without receiving its start marker. The same USB network still answered ICMP and the NFS server remained running. These observations do not establish whether the desktop or rescue shell was responsive, nor do they identify the cause of the console timeout. No reboot was initiated for that check.

After that timeout, the user confirmed that the desktop still responds to touch. This establishes that the visible interface was responsive at that later moment; the cause of the console timeout remains unknown.

The incremental single-worker upstream kernel retry completed successfully. The upstream module installer staged 69 modules for `7.3.0-rc1-orchard-apple-16k`, and the matching tree was placed in the separate private test root with root ownership. The NFS runtime selected five client modules and their staged hashes matched the kernel tree. A new private image assembled from the upstream loader, verified no-charge J71s tree, built kernel and staged NFS runtime passed component-receipt, initramfs-framing and module-path checks. These are offline checks; the image has not been booted on the iPad, and the current NFS export must not be switched while the current desktop is using it.

The staged module tree includes the Apple Z2 touch, TSL2583 light-sensor and CS42L81 codec modules. Its generated module aliases include the `apple,j71t-touchscreen` and `apple,ct819` compatibles used in the shared tree. This is an autoload metadata check, not evidence of successful probing or device function.

The J71s source does not define the shared S8003-only PCIe inclusion flag. Inspection of the compiled test tree found no PCIe, ANS or NVMMU compatible node, and confirmed that the charger node is disabled. The tree retains PCIe-related power-domain definitions; their presence alone is not an enabled PCIe host. These checks do not qualify storage, charging or the safety of other enabled devices.

The source used for this physical build contains the upstream dedicated `tcr_lock` implementation accepted after [linux PR 1](https://github.com/OrchardLinux/linux/pull/1); the current unified upstream patch retains that lock. The maintainer reported successful DART tests on J71b. Since PCIe is disabled in this J71s boot, the presence of the corrected code does not demonstrate J71s PCIe DART attachment or DMA. Do not replace it with the older experimental patch that reused the general DART lock.

While the existing iPad desktop remained connected to its original server, a separate NFSv4 server bound only to host loopback exported the private upstream test root. A read-only `nfs-ls` client listed the root receipt, systemd executable and matching module dependency and alias files, reporting UID/GID 0:0 for those files. The temporary server was stopped afterward. This checks export visibility and reported ownership from a local client; it does not establish iPad connectivity or a successful handoff.

The user restarted into iPadOS, where the battery reported 55%, and put the iPad in DFU. The upstream-based RAM image booted with kernel `7.3.0-rc1-orchard-apple-16k`; the NFS and NFSv4 modules loaded, and the isolated USB network and new NFS export responded. The kernel reported 47% battery. Manual handoff reached systemd `running`, with no failed units and no retained `nfs: server` timeout lines at the sampled time. The initial post-handoff console check timed out while the rescue shell restarted; a subsequent check succeeded.

On this upstream-based physical boot, read-only inventory found an `iPad6,11 Touchscreen` input device, a sound card named `iPad5 Speakers`, an `hci0` Bluetooth controller and a `ct819` IIO light sensor. The log reports that the sensor loaded LSCI v2 calibration and was found; one illuminance read returned zero. `labwc`, the on-screen keyboard, PipeWire and `omarchy-shell` were running. These observations show detection and processes, not working touch interaction, sound playback, Bluetooth pairing or accurate light readings. The user observed startup text before stepping away; visual desktop confirmation remains pending.

Later in the same boot, a private Wayland compositor screenshot showed the
rendered desktop wallpaper and panel at 1536 by 2048. The temporary copy on
the NFS root was removed; the screenshot remains private. This confirms the
compositor output, not that the physical display showed it or that touch was
responsive. A subsequent sysfs check reported the DRM connector connected and
enabled, and the backlight powered with actual brightness 1569 of 2047. Those
are driver-reported states, not direct observation of the panel.

ALSA reports a playback and capture PCM for the speaker card, and the Bluetooth radio reports neither software nor hardware blocked. A first NFS write probe did not run because the rescue shell's restricted PATH omitted the utilities; no file was created. A retry using absolute paths wrote and synced 4 MiB of random data as the tablet user: tablet and host SHA-256 matched, and the host saw UID/GID 1000:1000 and mode 0600. The temporary file was removed. This verifies one transfer through the new kernel and NFS setup, not long-term storage reliability.

At approximately 110 minutes of the same boot, a second probe wrote and synced 16 MiB of random data as the tablet user. The tablet's SHA-256 matched a checksum computed in the NFS server's user namespace and the host observed the expected size; the tablet removed the file and the host confirmed its absence. A direct host-user read failed due to namespace ownership, so the server-side checksum was used. This exercises a larger transfer on the upstream-based boot, not internal storage or a controlled NCM congestion test.

In a separate reverse-direction check on the same boot, the NFS server's tablet UID created and synced a 16 MiB random file, and the iPad's tablet user read it and calculated the same SHA-256. The server removed the file and the host confirmed its absence. This samples server-to-iPad reads in addition to the earlier write; it is not a sustained throughput test or a test of internal storage.

Bluetooth's userspace controller reports powered on, but pairing and transfers remain untested. PipeWire reported a default built-in stereo sink. A raw silent-stream attempt exited 1 without a useful error; a separate one-second silent WAV played through `pw-play` as the tablet user and exited 0. Its temporary file was removed. The latter verifies the command completed through PipeWire; it does not prove audible speaker output or microphone capture.

A later short Bluetooth discovery command reported that discovery started;
after it stopped, the controller reported powered and not discovering. The
temporary command output was removed and no discovered device details were
included in this record. This checks start/stop of discovery, not reception,
pairing or data transfer. The daemon had written two cache files during the
test window; those files were subsequently removed without recording their
contents. Other daemon persistence behavior was not evaluated.

At a later sample in the same boot, the CT819 sensor reported illuminance input 180 and IR raw 59, after the earlier illuminance input of zero. This shows readable and changing values, but the lighting conditions and accuracy were not independently measured.

The running Linux device tree's `apple,als-calibration` property also matched
the saved private ADT's single `alsCalibration` property by length and digest.
Together with the driver's LSCI v2 load message, this confirms the calibration
input reached this boot; it does not establish illuminance accuracy.

The new touchscreen input device reports both single-touch and multitouch coordinate ranges of X 0–1535 and Y 0–2047, matching the display's 1536-by-2048 pixel dimensions. This is an axis-range check; orientation, calibration and user interaction still need confirmation on the upstream-based boot.

The live upstream-based Linux device tree contained one `apple,z2-cal-blob`.
Its length and SHA-256 matched the `multi-touch-calibration` property in the
saved private J71s ADT. This verifies that the calibration bytes reached the
running Linux tree in this boot; the calibration itself and its digest remain
private, and this does not prove touch accuracy or interaction.

At approximately 48 minutes of uptime in the upstream-based boot, the rescue console reported systemd `running`, 41% battery and no `nfs: server` timeout lines in the retained kernel log. Three USB-network pings completed without loss. This is a point-in-time sample; the kernel ring buffer may not retain all earlier messages and it does not establish uninterrupted long-term reliability.

At approximately 63 minutes of uptime in the same boot, a 100-packet USB
network sample had no observed packet loss. The rescue console then reported
systemd `running`, 40% battery and no retained NFS server timeout lines. This
is one short network sample and a log snapshot, not proof of long-term stability
or a controlled comparison with an unpatched kernel.

A later search of retained kernel messages for errors and failures returned a
systemd-journald warning that setting an ACL on the tablet user's journal was
not supported. No other matching lines were present in that sample. The system
was reported running, but the effect on unprivileged journal access and the
source of the unsupported ACL operation have not been established. Kernel
ring-buffer retention and the search terms limit this observation. A subsequent
`journalctl --user` check as the tablet user exited 1 and reported insufficient
permission to open any journal files. This demonstrates the access failure in
this setup, but does not by itself prove that the earlier ACL warning caused it.
The local NFS server's VFS source says its `setAcl` does not store ACLs; how
that implementation relates to this Linux client's specific ACL request has
not been traced. No broader journal permissions were granted as a workaround.

The client reports the per-user journal file as UID/GID 0:0, mode 0640, with
only the basic owner/group/other ACL entries; the tablet user is in neither
the root nor systemd-journal group. Those observed permissions explain why
this user cannot read that file. The journal directories were traversable;
the exact protocol-level reason for the failed ACL update remains unverified.

Systemd's [journal configuration documentation](https://www.freedesktop.org/software/systemd/man/latest/journald.conf.html) states that per-user journals require persistent storage; `Storage=volatile` uses a single volatile journal and makes `journalctl --user` unavailable. Consequently, moving journald to volatile storage alone is not a fix for the observed user-journal access failure, even if it avoids NFS ACL operations. Persistent storage with working per-user access control, or a consciously chosen different logging arrangement, still needs investigation. No journal configuration was changed on the running tablet.

To isolate the access-control operation, a root shell on this boot created a new private temporary file on the NFS root and ran `setfacl -m u:1000:r` on it. The command returned `Operation not supported` and exit 1; `getfacl` reported only owner/group/other entries. The probe file was removed and its absence confirmed on the host. This reproduces a named-user POSIX ACL failure independently of journald on this specific client/server mount, but does not identify the exact NFS protocol response or prove the same limitation for other servers or filesystems.

The tested kernel source supplies a stronger client-side explanation: NFSv4 regular-file inode operations have no POSIX `set_acl` callback, and the VFS `set_posix_acl` path returns `EOPNOTSUPP` when that callback is absent. The NFSv4 client exposes a distinct NFSv4 ACL interface; the server's separate lack of ACL storage is an additional limitation, not sufficient on its own to explain this POSIX `setfacl` failure. This source tracing is consistent with the physical result and means replacing only the server should not be assumed to make POSIX ACL-based journald access work on this client. No packet capture or alternate-server physical test was performed.

An upstream refresh found hardware main at `4f15a70`, a descendant of the tested `0cfb171`. The intervening history reorganizes the CLI and hardware Python code into one project. In the compared paths there are no changes to the kernel or m1n1 patch directories or the NFS runtime shell scripts; the NFS staging Python moved to `orchard.image.nfs` and now writes `orchard.local.toml`. Reproduction instructions must account for that interface change. This comparison does not test the newer tooling or establish equivalence outside the inspected paths.

In a separate checkout of upstream `4f15a70`, all 13 NFS runtime tests passed. Staging the same private root identity, BusyBox, kernel and network parameters with `orchard.image.nfs` produced byte-identical runtime files to the physically booted staging output; the device-choice file's contents also matched under its new filename. This validates staging for these inputs, not a physical boot assembled with the newer project's complete build workflow.

The newer module-staging recipe also processed the existing upstream kernel output and staged 69 modules. All 82 generated files in its module tree matched the previously staged module tree byte-for-byte. This comparison does not rebuild the kernel or validate the complete updated build workflow.

The unified checkout's RAM build tests initially produced four CLI errors because the source-only test environment had no installed `orchard` package metadata. Supplying temporary metadata matching its declared version 0.2.0 allowed all 38 tests to pass. This is a source-checkout test with synthetic package metadata, not a test of installing the package or booting an image.

The running upstream-based boot exposes an `apple-vxd` video4linux device and PipeWire lists it. The selected kernel-log search returned no matching VXD messages. Device enumeration does not prove video firmware initialization or successful hardware decoding.

A read-only V4L2 format query of that device advertised H.264 parsed slice input (`S264`) and NV12 capture output. This verifies the advertised interface only; no encoded video was submitted and hardware decoding has not been demonstrated.

The installed GStreamer inspection command did not find a `v4l2codecs` plugin, and the displayed FFmpeg decoder list included `h264_v4l2m2m`. No compatibility between that FFmpeg wrapper and the driver's parsed-slice interface was established. An appropriate stateless client and a decode fixture are still needed before claiming hardware playback.

The private root contains the recipe's `apple/vxd-deva.bin` at the firmware path requested by the driver; firmware loading was not observed. The `libgstv4l2codecs.so` file was not found in its GStreamer plugin directory. The video node reports stateless H.264 controls including frame-based decode mode. These are file and interface checks, not a decode test.
