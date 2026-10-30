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
