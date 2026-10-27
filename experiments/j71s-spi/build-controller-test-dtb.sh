#!/usr/bin/env bash
# Experimental controller-only RAM boot: this WILL power and initialize SPI3.
set -euo pipefail
if (( $# != 3 )); then
  echo 'Usage: bash build-controller-test-dtb.sh KERNEL_INCLUDE J71S_BASE_DTB OUTPUT_DTB' >&2
  exit 2
fi
headers=$(realpath "$1")
base=$(realpath "$2")
output=$3
[[ -d "$headers/dt-bindings" && -f "$base" && ! -e "$output" && ! -L "$output" ]] || exit 1
here=$(cd "$(dirname "$0")" && pwd)
bash "$here/check-disabled-dtb.sh" "$headers" "$base"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cp "$base" "$work/base.dtb"
cp "$here/j71s-spi3-disabled.dtso" "$work/spi.dtso"
"${ORCHARD_PYTHON:-python3}" -m orchard_hardware.buildenv run \
  --bind "$headers:/headers:ro" --bind "$work:/out:rw" \
  --image localhost/orchard-hardware-kernel-toolchain:bookworm -- bash -euc '
    clang-19 -E -P -x assembler-with-cpp -nostdinc -undef -D__DTS__ \
      -I "$ORCHARD_HEADERS" "$ORCHARD_OUT/spi.dtso" -o "$ORCHARD_OUT/spi.dts"
    dtc -@ -I dts -O dtb -o "$ORCHARD_OUT/spi.dtbo" "$ORCHARD_OUT/spi.dts"
    fdtoverlay -i "$ORCHARD_OUT/base.dtb" -o "$ORCHARD_OUT/result.dtb" "$ORCHARD_OUT/spi.dtbo"
    [[ $(fdtget -t s "$ORCHARD_OUT/result.dtb" /soc/spi@20a08c000 status) == disabled ]]
    [[ $(fdtget -t s "$ORCHARD_OUT/result.dtb" /spi3-candidate-clock status) == disabled ]]
    fdtput -t s "$ORCHARD_OUT/result.dtb" /spi3-candidate-clock status okay
    fdtput -t s "$ORCHARD_OUT/result.dtb" /soc/spi@20a08c000 status okay
    [[ $(fdtget -t s "$ORCHARD_OUT/result.dtb" /soc/spi@20a08c000 status) == okay ]]
    [[ $(fdtget -t s "$ORCHARD_OUT/result.dtb" /spi3-candidate-clock status) == okay ]]
    [[ -z $(fdtget -l "$ORCHARD_OUT/result.dtb" /soc/spi@20a08c000) ]]
    ! fdtget "$ORCHARD_OUT/result.dtb" /soc/spi@20a08c000 pinctrl-0 >/dev/null 2>&1
    [[ $(fdtget -t s "$ORCHARD_OUT/result.dtb" / compatible) == "apple,j71s apple,s8000 apple,arm-platform" ]]
  '
mkdir -p "$(dirname "$output")"
cp --no-clobber "$work/result.dtb" "$output"
echo "Experimental controller-only DTB: $output"
echo 'Booting it powers SPI3 and initializes its controller; no touch child or pinmux is configured.'
