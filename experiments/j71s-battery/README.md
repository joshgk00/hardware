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
`add-hdq-debug.py` can add temporary, disabled-by-default dynamic-debug probes
to an already prepared source checkout. On a kernel built with those probes,
`hdq-debug-probe.sh` enables them briefly for one battery status request, then
disables them and restores a read-only debugfs mount. It reports interrupt
status and receive-byte counts, not gauge values or private device data.

The selected patch subset was applied and compiled against the pinned kernel.
The overlay built successfully, its output properties were checked, and a
J72s base tree was rejected. A RAM-only image containing the experimental
kernel and overlay was assembled and its component hashes verified. None of
these checks constitutes a physical boot or battery-gauge validation.

On the first physical J71s RAM boot, Linux bound the S5L UART at
`0x20a0d4000`, selected GPIO 2 peripheral function 2, and registered a 1-Wire
slave and battery power-supply device. Those registrations alone did not prove
communication: status, capacity, voltage, current and temperature returned I/O
errors. One dynamically enabled HDQ debug message reported a transfer timeout
(`-ETIMEDOUT`). This does not identify whether the pin wiring, UART timing,
echo, gauge response or another part of the transport is responsible. The
experiment must not be presented as working battery support.
After those reads, Linux UART counters showed 80 transmitted bytes and zero
received bytes. This narrows the failure to the receive path or earlier
electrical/transport behavior; it does not prove which component is at fault.
On a second RAM boot with opt-in diagnostic probes, a fresh battery request
timed out with zero received bytes recorded by the HDQ driver. No UART IRQ
status message appeared for that request; the transmitted byte counter rose.
The gauge driver's five-second cache must expire before a diagnostic request
can force another transfer.
For further comparison, [Project Cascadia's older iPad mini driver](https://github.com/rzxvx/Project-Cascadia/blob/2d2e875e85f8a8e1f5cab063c14a519c72871b5e/patches/files/drivers/power/supply/apple-hdq-battery.c)
uses direct UART polling and different initialization on its A5 device. Its
success is not evidence that the same register settings are safe or correct
for S8000; the J71s receive path still needs investigation.

The reused gauge driver provides only its read callback, not a gauge-write
callback. Nevertheless, the experiment configures UART/pinctrl and transmits
HDQ read commands. The electrical behavior, UART timing, gauge values and
failure handling are unverified on J71s. Validate those separately before
considering a normal device target or publishing a claim of battery support.
