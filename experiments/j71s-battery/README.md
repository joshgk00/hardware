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
can force another transfer. Three additional requests after cache expiry each
timed out with zero received bytes, so the observed failure was repeatable.
For further comparison, [Project Cascadia's older iPad mini driver](https://github.com/rzxvx/Project-Cascadia/blob/2d2e875e85f8a8e1f5cab063c14a519c72871b5e/patches/files/drivers/power/supply/apple-hdq-battery.c)
uses direct UART polling and different initialization on its A5 device. Its
success is not evidence that the same register settings are safe or correct
for S8000; the J71s receive path still needs investigation.
That older implementation checks its receive-ready status directly and warns
that its Apple FIFO status layout differs from Samsung's. The current J71s
experiment uses the generic S5L UART driver's FIFO and interrupt path. This is
a comparison to investigate, not evidence that the same difference applies to
S8000 or that data reached the receive FIFO.
In one J71s request, 300 discrete read-only samples of the UART status and FIFO
registers saw no RX-ready or RX-FIFO bits under the Linux driver's masks, and
two samples showed TX-FIFO activity. The samples can miss short events, the
mask interpretation is not independently verified for S8000, and no receive
data register was read. `hdq-status-sample.sh` repeats this bounded experiment.
The independently built `uart-sampler.c` makes 6,000 read-only status samples
with a 100-microsecond requested sleep, checking the J71s compatible string
and bound UART driver first. When run around a fresh battery request twice,
it recorded zero RX-ready and RX-FIFO indications and nine TX-FIFO samples each
time. Scheduling gaps and concurrent driver reads mean brief receive events
can still be missed; the result does not establish an electrical cause.
One further run also sampled GPIO 2's data bit and observed it high in all
6,000 samples. Its meaning while the pin is muxed to a peripheral is not
verified, so this does not prove that the physical line stayed high.
In the J71s diagnostic boot, read-only snapshots of the configuration
registers already read by the Linux UART driver reported ULCON `0x07`, UCON
`0x1885`, UFCON `0x31`, and UBRDIV `0x19`. The A5 polling example uses ULCON
`0x07`, UCON `0x405`, UFCON `0x01`, and UBRDIV `0x19`. The control and FIFO
differences are observations only: they are on different SoCs and support
different interrupt strategies, so copying settings would not establish a
safe or correct J71s configuration. No register values were changed.
The GPIO controller's read-only configuration for pin 2 reported peripheral
function 2, input-enable set, and pull code 0. This confirms what Linux
programmed, not that function 2 is the correct electrical connection or that
the battery line has a suitable external pull-up.

The prior J71s UCON snapshot had bit 10 clear. A [Linux UART patch by Yureka
Lilian](https://lists.openwall.net/linux-kernel/2026/10/02/2066) reports that
the S5L driver can clear this undocumented bootloader-set bit and that keeping
it matters on another Apple SoC. `preserve-ucon.py` prepares that published
preservation change and a J71s-specific boot log of the bit before reset. It
does not force the bit on. Whether the bootloader sets it on this iPad, or
whether preserving it affects HDQ, was tested on a separate RAM boot. Before
the UART reset, the boot log reported bit 10 set; the running driver retained
it. A fresh HDQ request still timed out with zero received bytes. This confirms
preservation on the tested J71s but does not identify the bit's purpose or
establish functional battery communication. A fast read-only sample during
another request again found TX FIFO activity but no RX-ready or RX-FIFO bits;
the sampling limitations above still apply.

`log-pin-before-mux.py` prepares an additional diagnostic that reports GPIO 2's
peripheral function, input-enable bit and pull setting immediately before the
Linux pinctrl driver applies the experimental UART mux. It only reads that
configuration; the actual pinctrl operation is unchanged. The resulting
kernel needs a physical RAM boot before any conclusion can be drawn.

The reused HDQ driver's receive decoder treats bytes `>= 0xf0` as a one.
TI's [HDQ UART application note](https://www.ti.com/lit/an/slua408/slua408.pdf)
lists `0xf0` among possible zero encodings and uses a threshold above `0xf8`.
Under those documented examples the current decoder would misinterpret
`0xf0`. This may need a separate decoder fix if bytes are received; it cannot
explain the present zero-byte timeout, and actual J71s timing is unverified.

The reused gauge driver provides only its read callback, not a gauge-write
callback. Nevertheless, the experiment configures UART/pinctrl and transmits
HDQ read commands. The electrical behavior, UART timing, gauge values and
failure handling are unverified on J71s. Validate those separately before
considering a normal device target or publishing a claim of battery support.
