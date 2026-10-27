#!/usr/bin/env bash
# Build a J71s DART domain-attachment test, with no physical DMA consumer.
set -euo pipefail
if (( $# != 3 )); then
  echo 'Usage: bash build-software-consumer-dtb.sh KERNEL_INCLUDE J71S_BASE_DTB OUTPUT_DTB' >&2
  exit 2
fi
headers=$(realpath "$1")
base=$(realpath "$2")
output=$3
[[ -d "$headers/dt-bindings" && -f "$base" && ! -e "$output" && ! -L "$output" ]] || exit 1
here=$(cd "$(dirname "$0")" && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cp "$base" "$work/base.dtb"
cp "$here/j71s-dart-consumer-test.dtso" "$work/test.dtso"
"${ORCHARD_PYTHON:-python3}" -m orchard_hardware.buildenv run \
  --bind "$headers:/headers:ro" --bind "$work:/out:rw" \
  --image localhost/orchard-hardware-kernel-toolchain:bookworm -- bash -euc '
    tree="$ORCHARD_OUT/result.dtb"
    [[ $(fdtget -t s "$ORCHARD_OUT/base.dtb" / compatible) == "apple,j71s apple,s8000 apple,arm-platform" ]]
    [[ $(fdtget -t u "$ORCHARD_OUT/base.dtb" /soc "#address-cells") == 2 ]]
    [[ $(fdtget -t u "$ORCHARD_OUT/base.dtb" /soc "#size-cells") == 2 ]]
    for node in /soc/iommu@601008000 /soc/j71s-dart-software-consumer /soc/pcie@610000000; do
      if fdtget -t s "$ORCHARD_OUT/base.dtb" "$node" compatible >/dev/null 2>&1; then
        echo "Conflicting base node $node" >&2; exit 1
      fi
    done
    clang-19 -E -P -x assembler-with-cpp -nostdinc -undef -D__DTS__ \
      -I "$ORCHARD_HEADERS" "$ORCHARD_OUT/test.dtso" -o "$ORCHARD_OUT/test.dts"
    dtc -@ -I dts -O dtb -o "$ORCHARD_OUT/test.dtbo" "$ORCHARD_OUT/test.dts"
    fdtoverlay -i "$ORCHARD_OUT/base.dtb" -o "$tree" "$ORCHARD_OUT/test.dtbo"
    dart=/soc/iommu@601008000
    consumer=/soc/j71s-dart-software-consumer
    [[ $(fdtget -t s "$tree" "$dart" compatible) == "apple,s8000-dart apple,s5l8960x-dart" ]]
    [[ $(fdtget -t x "$tree" "$dart" reg) == "6 1008000 0 4000" ]]
    [[ $(fdtget -t x "$tree" "$dart" interrupts) == "0 f5 4" ]]
    [[ $(fdtget -t s "$tree" "$dart" status) == okay ]]
    [[ $(fdtget -t s "$tree" "$consumer" compatible) == "orchard,j71s-dart-test" ]]
    [[ $(fdtget -t s "$tree" "$consumer" status) == okay ]]
    [[ $(fdtget -t x "$tree" "$consumer" iommus) == "$(fdtget -t x "$tree" "$dart" phandle) 0" ]]
    domain=$(fdtget -t s "$tree" /__symbols__ ps_pcie)
    [[ $(fdtget -t x "$tree" "$domain" reg) == "80310 4" ]]
    [[ $(fdtget -t x "$tree" "$dart" power-domains) == $(fdtget -t x "$tree" "$domain" phandle) ]]
    check_consumers() {
      local path=$1 child next
      if fdtget "$tree" "$path" iommu-map >/dev/null 2>&1; then
        echo "Unexpected IOMMU map at $path" >&2; return 1
      fi
      if [[ "$path" != "$consumer" ]] && fdtget "$tree" "$path" iommus >/dev/null 2>&1; then
        echo "Unexpected IOMMU consumer at $path" >&2; return 1
      fi
      for child in $(fdtget -l "$tree" "$path"); do
        if [[ "$path" == / ]]; then next="/$child"; else next="$path/$child"; fi
        check_consumers "$next" || return 1
      done
    }
    check_consumers /
  '
mkdir -p "$(dirname "$output")"
( set -o noclobber; cat "$work/result.dtb" > "$output" )
echo "Experimental software-only IOMMU consumer tree: $output"
echo 'Booting attaches stream 0 and writes DART translation/TLB registers; it may hang and require DFU recovery.'
