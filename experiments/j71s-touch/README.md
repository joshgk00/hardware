# Experimental iPad 5 J71s N1 touchscreen

This is bring-up research, not an installer or a supported device profile. It targets J71s (iPad6,11, S8000, DFU chip 0x8000), not the J71t S8003 variant. The existing J71t work is from [hardware PR 6](https://github.com/OrchardLinux/hardware/pull/6), head `f764d95f70616adae483a97aaa7dae9f18cc8114`, and [the author's N1 protocol documentation](https://github.com/brkosebay/omarchy-ipad5/blob/main/docs/touch/n1-protocol.md). The test used that PR's kernel patches 0003 (SmartIO/SPI) and 0004 (N1 touch) against Orchard's pinned Hoolock kernel `6831bc701a6ce059e71e5aaa9488c9195bea6927`, with this branch's prior J71s battery changes.

## Physical results

On one J71s, the stage-1 RAM test initialized SPI3 and read touchscreen bootloader identity `0x434d15c1`. A subsequent stage-2 RAM test loaded that device's firmware and 1024-byte calibration, received calibration transport status `0x4969`, executed the firmware, and discovered interface 1, packet limit 2454, family 21, 40x30 sensor, firmware version 0x210, and 14745x19657 surface. Stage 2 powered down before creating an input device. This is not evidence that calibration is correct, touch events work, orientation is correct, or an installed system runs.

The stage-3 RAM image booted on this J71s and registered the N1 input device. During user taps and drags a bounded capture reached 512 events, 72 frames, six contact starts, five contact ends and zero SYN_DROPPED reports; the limit may truncate the final contact. The GPIO 65 interrupt counter was 297 afterward. This verifies physical touch events on one unit, not corner mapping, desktop integration or long-term stability. The test tree inherits the J71t Y inversion, which needs physical corner testing. Firmware and device calibration are private inputs and must not be committed, published, or copied from another iPad.

## Draft artifacts

- `j71s-n1-draft.dtso`: disabled offline device-tree draft based on the J71t wiring and independently observed J71s Apple device-tree properties. Its regulator, clock, SPI controller and touch child are disabled; it is not a boot-ready overlay.
- `j71s-n1-match-draft.patch`: matches J71s and forces identification-only stage 1. Apply after the upstream N1 driver patch.
- `j71s-n1-pinctrl-draft.patch`: adapts the J71t S8000 display-sync mux behavior to only J71s AP GPIO 74, retaining the earlier battery GPIO behavior. It targets the J71s battery-modified GPIO source; this narrow adaptation is experimental.
- `j71s-n1-stage2-draft.patch` and `j71s-n1-stage3-draft.patch`: sequentially change the forced stage. Stages 2 and 3 have the physical results above.
- `j71s-touch-capture.sh` and `j71s-touch-report.py`: bounded input capture and host-side ARM64 evdev summary. The missing-device and BusyBox timeout paths were checked; one real input capture produced the event counts above.

Neither stage proves storage, Wi-Fi, charging or a persistent Omarchy installation. In particular, J71s PCIe remains unresolved; the J71t host driver and device tree cannot be assumed to support S8000.
