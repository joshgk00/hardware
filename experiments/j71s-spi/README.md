# Experimental J71s SPI groundwork

The iPad 5 Wi-Fi S8000 tree identifies the same legacy SPI controller family
as the iPad Air 2 J81. An [independent J81 project](https://github.com/mattonik/ipad-nixos/tree/b94d42f78e04c5465e290340a5b6879bbc5956b6)
has a legacy SPI patch and follow-up fixes. `prepare-spi.sh` applies precisely
those three patches to an isolated checkout of the pinned Hoolock kernel. It
checks both revisions, each patch hash, the original source hash and the
resulting source hash. The third patch applies with line offsets. It does not
create a device tree node or enable any hardware.

The driver object and a full kernel image built with the Orchard J71s config and
LLVM 19, combined with the separate experimental battery changes. A successful build does not prove that
the controller, clocks, touch power or firmware sequence work on J71s. The J81
board uses different GPIOs and a different PMU; do not copy its settings.

The reference project retains authorship and licensing of its patches. Keep
firmware, device-specific trees and calibration data private. This is not an
installer or device support.

`j71s-spi3-disabled.dtso` is an offline-only structure candidate. Both the
controller and its tentative fixed clock are disabled; there is no pinmux or
touch child. Offline decoding of the private J71s Apple tree with m1n1 maps
SPI3 gate ID 77 to `0x20e0801d0` and its parent SIO_P to `0x20e080158`.
Those addresses and the parent relationship match the S8000 Linux tree's
`ps_spi3` and `ps_sio_p` descriptions. This is evidence for the association,
not an active power test. The clock rate still requires independent hardware
validation. `check-disabled-dtb.sh` rejects non-J71s
trees and preexisting SPI3 nodes, compiles the overlay, verifies the relevant
values and disabled states, and discards the result. Do not turn the nodes on
or use this as a boot image based on the structural check alone.

`build-controller-test-dtb.sh` builds a distinct controller-only RAM-test
tree after the disabled check succeeds. Booting it powers the SPI3 domain and
the driver writes controller initialization registers. It sets no SPI pinmux,
instantiates no touch child, sends no SPI transfer, and does not implement
touch. Its clock rate, interrupt behavior and register semantics remain
unverified for J71s; a failed boot may require returning to DFU mode. The
test tree must not be used as an installer or merged into normal support.
`controller-probe.sh` inspects the platform binding, SPI master and related
kernel messages after such a boot. It issues no transfer and does not touch
the touchscreen power or pins. Controller registration alone does not prove
that the clock, transfers, firmware or touchscreen work.
On the existing battery-only J71s RAM boot, the probe reported no SPI3
platform device or SPI master. This establishes the baseline for a later
controller-only test; it does not test the prepared controller image.

On a subsequent controller-only J71s RAM boot, Linux bound `apple-spi` to
`20a08c000.spi` and registered `spi0` under that controller. No SPI child
devices were present, and the controller's runtime status was suspended when
checked. The battery gauge and USB serial remained available. This is one
successful initialization on one iPad, not a test of IRQs, clock rate, pinmux,
SPI transfers, touch power, firmware, or touchscreen input.
Read-only pinctrl metadata also showed the identified touch IRQ, power, sync,
reset and chip-select lines (65, 73, 74, 75 and 102) as unclaimed after the
controller boot. "Unclaimed" does not reveal their electrical state.
