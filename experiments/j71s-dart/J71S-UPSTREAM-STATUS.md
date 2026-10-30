# iPad 5 J71s: upstream-based RAM boot status

This is a bring-up summary for the Wi-Fi iPad 5 A1822 (`apple,j71s`, S8000).
It is not an installer or a claim of complete device support. The detailed
evidence and limitations are in [NFS-PHYSICAL-TEST.md](NFS-PHYSICAL-TEST.md)
and [storage-integration.md](storage-integration.md).

## Tested setup

One physical boot used hardware revision `0cfb17118261ac37e1d5019d45c63237fb550c73`,
its J71s device tree and integrated J71t `apple_z2` touchscreen support, a
matching m1n1 build and device-specific firmware. The kernel also included
[Francesco Lavra's proposed USB NCM timer change](https://patchew.org/linux/20260727165441.1969927-1-flavra@baylibre.com/).
A test-only overlay disabled the unqualified J71s Lightning charger node.

The kernel ran from RAM and mounted an Omarchy root served by the host over an
isolated USB NCM link. The root and rescue shell are not authenticated; this
setup is appropriate only on a trusted isolated connection. No internal disk
installation was performed. Firmware, device-specific calibration and raw
logs remain private.

## Observations

- Systemd reached `running` with no failed units at the sample; `labwc`, the
  on-screen keyboard and Omarchy shell processes were present. A private
  compositor screenshot showed the rendered desktop; confirmation on the
  physical screen and interactive touch remain pending.
- The touchscreen enumerated with X 0–1535 and Y 0–2047 axes, matching the
  display dimensions. Its live calibration property matched the saved private
  device-tree calibration by length and digest. That does not establish
  correct orientation, accuracy or touch interaction.
- The speaker card, Bluetooth controller and calibrated ambient light sensor
  enumerated. Bluetooth reported powered; one silent WAV playback command
  completed; sensor values changed. Audible output, pairing, microphone and
  light-sensor accuracy remain untested.
- The video decoder exposed stateless H.264 and NV12 formats. No video decode
  was performed.
- A 4 MiB random write as the tablet user matched the host checksum and
  ownership. At approximately 63 minutes, 100 USB pings had no loss and the
  retained kernel log had no NFS timeout lines. These are limited samples.
- The tablet user could not read its journal: the observed journal file was
  root-owned and lacked a user ACL after journald reported an unsupported ACL
  operation. The exact NFS protocol cause has not been established.

## Remaining work

- Confirm screen, touch orientation, keyboard and audible output on the new
  boot; test Bluetooth and the sensor against physical conditions.
- Implement and validate S8000 PCIe host description and driver matching,
  power/reset sequencing, DMA ownership and translation, interrupts and
  teardown. The related S8003 implementation does not establish S8000
  compatibility. Previous S8000 diagnostics saw a storage endpoint and BAR,
  but did not demonstrate a completed disk command.
- Bring up PCIe port 1 and Wi-Fi after validating its signals and sequencing;
  compare the private ADT with `check-wlan-signals.py` without publishing it.
- Qualify charging and internal storage, then test an installer before
  describing the device as installable. Do not use the charger override as a
  charging implementation.
- Reconcile the reproducible changes with current upstream and maintainer
  feedback before proposing a focused contribution. The newer unified
  upstream staging interfaces have passed local checks, but the complete
  updated build workflow has not been physically tested.
