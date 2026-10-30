# iPad 5 Wi-Fi (J71s) upstream-based RAM boot

This is a single-device bring-up record, not an installation guide or a claim
that J71s is supported. The tested device is an A1822 with the Samsung S8000
SoC. J71t uses the related S8003; results cannot automatically be transferred
between them.

## Test setup

One physical boot used Orchard hardware revision `0cfb17118261ac37e1d5019d45c63237fb550c73`,
including the shared iPad 5 device tree and integrated `apple_z2` support,
with its matching m1n1, privately extracted device firmware and calibration.
The kernel additionally included Francesco Lavra's [proposed USB NCM timer
change](https://patchew.org/linux/20260727165441.1969927-1-flavra@baylibre.com/).
A test-only overlay disabled the J71s charging node. The device booted from
RAM and used a host-served NFS root over a dedicated USB connection. The NFS
export and rescue shell were unauthenticated and used only on a trusted,
isolated link. This was not an internal-storage installation.

The kernel base was `cee9395acd8043be0644b25c34bfa86623f2b935` with the
ordered Orchard patches for that hardware revision and the additional NCM
change above. The resolved config SHA-256 was
`e3e1f8bd1732a6cc2a9c389af53b81c9ac3cfad0e934029eab3ce6c6f18b01ef`;
the uncompressed kernel Image SHA-256 was
`68688e636de6a05dc7006c603dcca0d74a058c3e3683a127969e095d501ff15e`.
The boot release was `7.3.0-rc1-orchard-apple-16k`. The root was a private
J71b Omarchy image adapted for this J71s experiment, with the J71b charging
lease disabled. This record is on a later source revision than the physical
test; it does not claim that later revision was booted.

## Observations

- Systemd reported `running` without failed units. The compositor, on-screen
  keyboard and Omarchy shell were running, and a compositor screenshot showed
  the desktop. Physical display and touch interaction on this exact boot were
  not independently confirmed.
- At a later sample, after about 3 hours and 7 minutes of uptime, systemd
  still reported `running`, the battery gauge reported 24%, and the retained
  kernel log contained no NFS server timeout lines. This sample does not prove
  uninterrupted operation, and the disabled charger was not tested.
- The touchscreen registered with axes matching the display dimensions; the
  live calibration property matched the private device calibration. This does
  not establish orientation or touch accuracy.
- The audio card, Bluetooth controller and ambient light sensor enumerated.
  Bluetooth discovery started and stopped, a silent audio playback command
  completed, and sensor readings changed. Audible sound, microphone capture,
  pairing and sensor accuracy were not established.
- The only IIO device found in a later inventory was the `ct819` light sensor;
  no accelerometer or angular-velocity IIO channel was present. Other sensor
  interfaces were not exhaustively surveyed, and rotation was not tested.
  The private device ADT contains `accel`, `gyro` and `compass` nodes under an
  AOP nub, a possible lead for motion-sensor bring-up. Their presence does not
  identify the hardware protocol or establish compatibility with the proposed
  T8010 AOP driver.
  The saved iPadOS 16.7.16 restore archive contains an AOP firmware container
  named `aopfw-ipad6faop.im4p`; the J71b proposal uses a differently named
  container. The J71s AOP ADT compatible is `iop,s8000`. These are discovery
  inputs only: firmware format, protocol version, loading, DMA and sensor
  operation have not been validated, and no firmware is included here.
  Offline, Orchard's uncompressed IM4P parser accepted that container and its
  payload began with an OSSerializeBinary signature. The locally checked
  m1n1 OSSerialize parser stopped on unsupported object tag 8, so the firmware
  array could not be inspected with that parser. The [J71b rotation proposal's
  bounded parser](https://github.com/dl-alexandre/omarchy-a/blob/6734dd5c548731db6888d82c737f766c243c9234/desktop/aop/firmware.py)
  did parse the payload and found two firmware entries with header and data,
  labeled `AOP` and `AOP_ext`. This checks the container's broad structure,
  not the pinned J71b hashes, image internals, loading protocol or safety.
  The J71s AOP `reg` record contains four 64-bit address/size pairs. None is
  identical to the proposed J71b IOP, SRAM or auto-boot resource pair. This
  raw comparison does not account for parent address translation or establish
  equivalent resource semantics; J71b's addresses must not be copied to J71s
  without separate validation.
- The tablet user wrote and synced 16 MiB to the NFS root with a checksum
  matching the host; a separate 16 MiB host-created file also matched when read
  by the tablet. Both files were removed. A 100-packet USB ping sample had no
  observed loss. These are bounded checks, not a long-term reliability claim.
- The NFSv4 test mount rejected named-user POSIX ACLs. The tablet user could
  not read its user journal after journald reported an unsupported ACL. The
  tested Linux NFSv4 file operations lack a POSIX `set_acl` callback; this is
  a limitation of this test setup, not evidence about local storage.

## Remaining work

Confirm the physical display, touch and sound on the integrated boot. S8000
PCIe host matching, DMA translation, interrupt handling, internal storage,
Wi-Fi and charging remain unqualified. Earlier isolated link diagnostics
enumerated the storage endpoint but did not establish a completed storage
command. The charging override is not charging support. No installer has been
tested, and no support flag should be inferred from this record.

The NCM timer proposal was included in the tested image; a successful boot
alone does not establish that it caused the improvement or that its retry
path is safe. Firmware, device identifiers, calibration and raw logs are not
included in this document.
