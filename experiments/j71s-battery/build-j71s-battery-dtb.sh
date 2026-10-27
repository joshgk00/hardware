#!/usr/bin/env bash
# Build the J71s-only experimental battery overlay; never touches the iPad.
set -euo pipefail
if [[ $# != 3 && $# != 4 ]]; then
  echo 'Usage: bash build-j71s-battery-dtb.sh KERNEL_INCLUDE BASE_DTB OUTPUT_DTB [bootmux]' >&2
  exit 2
fi
headers=$(realpath "$1")
base=$(realpath "$2")
output=$3
[[ -d "$headers/dt-bindings" && -f "$base" && ! -e "$output" && ! -L "$output" ]] || exit 1
here=$(cd "$(dirname "$0")" && pwd)
overlay=j71s-battery-gauge.dtso
expected_pin=20002
if [[ $# == 4 ]]; then
  [[ "$4" == bootmux ]] || { echo 'Unknown overlay variant' >&2; exit 2; }
  overlay=j71s-battery-gauge-bootmux.dtso
  expected_pin=10002
fi
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cp "$base" "$work/base.dtb"
cp "$here/$overlay" "$work/gauge.dtso"
"${ORCHARD_PYTHON:-python3}" -m orchard_hardware.buildenv run \
  --bind "$headers:/headers:ro" --bind "$work:/out:rw" \
  --image localhost/orchard-hardware-kernel-toolchain:bookworm -- bash -euc '
    [[ $(fdtget -t s "$ORCHARD_OUT/base.dtb" / compatible) == "apple,j71s apple,s8000 apple,arm-platform" ]]
    clang-19 -E -P -x assembler-with-cpp -nostdinc -undef -D__DTS__ \
      -I "$ORCHARD_HEADERS" "$ORCHARD_OUT/gauge.dtso" -o "$ORCHARD_OUT/gauge.dts"
    dtc -@ -I dts -O dtb -o "$ORCHARD_OUT/gauge.dtbo" "$ORCHARD_OUT/gauge.dts"
    fdtoverlay -i "$ORCHARD_OUT/base.dtb" -o "$ORCHARD_OUT/result.dtb" "$ORCHARD_OUT/gauge.dtbo"
    [[ $(fdtget -t s "$ORCHARD_OUT/result.dtb" / compatible) == "apple,j71s apple,s8000 apple,arm-platform" ]]
    [[ $(fdtget -t x "$ORCHARD_OUT/result.dtb" /soc/serial@20a0d4000 interrupts) == "0 c5 4" ]]
    [[ $(fdtget -t s "$ORCHARD_OUT/result.dtb" /soc/serial@20a0d4000/onewire/fuel-gauge compatible) == "ti,bq27540-hdq" ]]
    pin=$(fdtget -t s "$ORCHARD_OUT/result.dtb" /__symbols__ battery_swi_pins)
    [[ $(fdtget -t x "$ORCHARD_OUT/result.dtb" "$pin" pinmux) == "$1" ]]
  ' bash "$expected_pin"
mkdir -p "$(dirname "$output")"
cp --no-clobber "$work/result.dtb" "$output"
echo "Experimental, untested J71s battery DTB: $output"
