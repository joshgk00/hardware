# Experimental J71s SPI groundwork

The iPad 5 Wi-Fi S8000 tree identifies the same legacy SPI controller family
as the iPad Air 2 J81. An [independent J81 project](https://github.com/mattonik/ipad-nixos/tree/b94d42f78e04c5465e290340a5b6879bbc5956b6)
has a legacy SPI patch and follow-up fixes. `prepare-spi.sh` applies precisely
those three patches to an isolated checkout of the pinned Hoolock kernel. It
checks both revisions, each patch hash, the original source hash and the
resulting source hash. The third patch applies with line offsets. It does not
create a device tree node or enable any hardware.

The driver object and a full kernel image built with the Orchard J71s config and
LLVM 19, combined with the separate experimental battery changes. The latter
image has not been packaged or booted. A successful build does not prove that
the controller, clocks, touch power or firmware sequence work on J71s. The J81
board uses different GPIOs and a different PMU; do not copy its settings.

The reference project retains authorship and licensing of its patches. Keep
firmware, device-specific trees and calibration data private. This is not an
installer or device support.
