# Unverified J71s HDQ battery experiment

This experiment targets only the S8000 iPad 5 Wi-Fi (`iPad6,11`, J71sAP).
It has not been tested on hardware and is not part of the normal build or an
installer. It does not add touchscreen, internal storage, Wi-Fi or charging
support. J71t and other boards need separate identification.

The J71s Apple device tree reports `gas-gauge,bq27540` / `gas-gauge,hdq` on
UART5. Address translation gives `0x20a0d4000`, with IRQ 197. The UART transmit
and battery single-wire functions both have GPIO argument 2 and raw function
argument 258. The overlay's pinmux function 2 is a hypothesis, not a confirmed
electrical mapping. The same gauge family appears in the J71b work, but its
interrupt and pin differ.

`prepare-j71s-hdq.sh` selects the HDQ-related pieces of the pinned J71b kernel
patch, checking both kernel revision and patch digest, for an isolated kernel
checkout. `build-j71s-battery-dtb.sh` builds the overlay with Orchard's kernel
toolchain, rejects non-J71s base trees and checks the output's IRQ, gauge
compatible and hypothesized pinmux. It expects the project's Python build
module, and `ORCHARD_PYTHON` can select the interpreter containing it.
`battery-probe.sh` reads battery status and relevant kernel messages in the
RAM test; it intentionally avoids raw device trees and calibration data.

The reused gauge driver provides only its read callback, not a gauge-write
callback. Nevertheless, the experiment configures UART/pinctrl and transmits
HDQ read commands. The electrical behavior, UART timing, gauge values and
failure handling are unverified on J71s. Validate those separately before
considering a normal device target or publishing a claim of battery support.
