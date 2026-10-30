# J71s USB NFS physical test record

This is a bring-up record, not an installation guide. It concerns an iPad 5
Wi-Fi J71s with the S8000 SoC. The root ran on a connected computer, not on
internal iPad storage. The tested NFS export and post-handoff rescue shell are
unauthenticated; this arrangement is for an isolated, trusted host only.

## Inputs

- Kernel base: Orchard Linux `6831bc701a6ce059e71e5aaa9488c9195bea6927`,
  plus the local J71s display/touch and hardware overlays used by this
  experiment. The source tree was modified; the base commit alone is not a
  complete reproduction recipe. A private snapshot now preserves the tracked
  diff, eight untracked source files and the config; a reverse/apply round trip
  reconstructed all 29 changed files byte-for-byte. A clean rebuild from that
  snapshot has not been performed, and the overlays need provenance and licensing
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

## Current upstream integration lead

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
have not yet been tested together. Keep the existing working NFS session until
a suitable image is prepared and verified.

The previously extracted J71s mtprops from the installed iPadOS 16.7.16 build matched the upstream recipe’s pinned input SHA-256. Orchard CLI `a2dd45f` converted it using the J71s recipe parameters, and the generated Z2FW matched the upstream expected SHA-256. The resulting firmware remains private. This validates the input and conversion only; it does not prove calibration handoff or touch operation with the integrated driver.

Using the current Orchard CLI, the S8000 SmartIO firmware was also extracted from the previously saved iPadOS 16.7.16 kernel cache; its digest matched the J71s upstream recipe. The firmware is kept private. This verifies a second test input, not SmartIO operation with an upstream-built kernel.

For the upstream comparison, the pinned Linux source `cee9395acd8043be0644b25c34bfa86623f2b935` was fetched, and all 358 ordered Orchard hardware `0cfb171` J71s patches passed `git apply --check` and applied to a separate tree. The proposed NCM timer patch also applied cleanly afterward. The upstream config makes NFS, SmartIO and the integrated touch driver modules, so the matching modules and firmware must be staged before physical testing. This source preparation is not a kernel build or device test.

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
