#!/usr/bin/env bash
# Offline-only structural check; the result must never enable SPI hardware.
set -euo pipefail
if (( $# != 2 )); then
  echo 'Usage: bash check-disabled-dtb.sh KERNEL_INCLUDE J71S_BASE_DTB' >&2
  exit 2
fi
headers=$(realpath "$1")
base=$(realpath "$2")
[[ -d "$headers/dt-bindings" && -f "$base" ]] || exit 1
here=$(cd "$(dirname "$0")" && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cp "$base" "$work/base.dtb"
cp "$here/j71s-spi3-disabled.dtso" "$work/spi.dtso"
"${ORCHARD_PYTHON:-python3}" -m orchard_hardware.buildenv run \
  --bind "$headers:/headers:ro" --bind "$work:/out:rw" \
  --image localhost/orchard-hardware-kernel-toolchain:bookworm -- bash -euc '
    [[ $(fdtget -t s "$ORCHARD_OUT/base.dtb" / compatible) == "apple,j71s apple,s8000 apple,arm-platform" ]]
    [[ $(fdtget -t u "$ORCHARD_OUT/base.dtb" /soc "#address-cells") == 2 ]]
    [[ $(fdtget -t u "$ORCHARD_OUT/base.dtb" /soc "#size-cells") == 2 ]]
    if fdtget -t s "$ORCHARD_OUT/base.dtb" /soc/spi@20a08c000 compatible >/dev/null 2>&1; then
      echo "Base already describes SPI3; refusing to overlay" >&2; exit 1
    fi
    if fdtget -t s "$ORCHARD_OUT/base.dtb" /spi3-candidate-clock compatible >/dev/null 2>&1; then
      echo "Candidate clock already exists; refusing to overlay" >&2; exit 1
    fi
    clang-19 -E -P -x assembler-with-cpp -nostdinc -undef -D__DTS__ \
      -I "$ORCHARD_HEADERS" "$ORCHARD_OUT/spi.dtso" -o "$ORCHARD_OUT/spi.dts"
    dtc -@ -I dts -O dtb -o "$ORCHARD_OUT/spi.dtbo" "$ORCHARD_OUT/spi.dts"
    fdtoverlay -i "$ORCHARD_OUT/base.dtb" -o "$ORCHARD_OUT/result.dtb" "$ORCHARD_OUT/spi.dtbo"
    [[ $(fdtget -t s "$ORCHARD_OUT/result.dtb" /soc/spi@20a08c000 status) == disabled ]]
    [[ $(fdtget -t s "$ORCHARD_OUT/result.dtb" /spi3-candidate-clock status) == disabled ]]
    [[ $(fdtget -t x "$ORCHARD_OUT/result.dtb" /soc/spi@20a08c000 reg) == "2 a08c000 0 4000" ]]
    [[ $(fdtget -t x "$ORCHARD_OUT/result.dtb" /soc/spi@20a08c000 interrupts) == "0 bf 4" ]]
    [[ $(fdtget -t u "$ORCHARD_OUT/result.dtb" /spi3-candidate-clock clock-frequency) == 61538461 ]]
    [[ -z $(fdtget -l "$ORCHARD_OUT/result.dtb" /soc/spi@20a08c000) ]]
    spi_domain=$(fdtget -t s "$ORCHARD_OUT/result.dtb" /__symbols__ ps_spi3)
    parent_domain=$(fdtget -t s "$ORCHARD_OUT/result.dtb" /__symbols__ ps_sio_p)
    [[ $(fdtget -t x "$ORCHARD_OUT/result.dtb" "$spi_domain" reg) == "801d0 4" ]]
    [[ $(fdtget -t x "$ORCHARD_OUT/result.dtb" "$parent_domain" reg) == "80158 4" ]]
    [[ $(fdtget -t x "$ORCHARD_OUT/result.dtb" /soc/spi@20a08c000 power-domains) == $(fdtget -t x "$ORCHARD_OUT/result.dtb" "$spi_domain" phandle) ]]
    [[ $(fdtget -t x "$ORCHARD_OUT/result.dtb" "$spi_domain" power-domains) == $(fdtget -t x "$ORCHARD_OUT/result.dtb" "$parent_domain" phandle) ]]
  '
echo 'Offline disabled SPI3 structure check passed; no boot image was produced.'
