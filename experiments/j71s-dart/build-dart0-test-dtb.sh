#!/usr/bin/env bash
# Build only a J71s DART0 probe tree; booting it writes DART registers.
set -euo pipefail
if (( $# != 3 )); then
  echo 'Usage: bash build-dart0-test-dtb.sh KERNEL_INCLUDE J71S_BASE_DTB OUTPUT_DTB' >&2
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
cp "$here/j71s-dart0-test.dtso" "$work/dart.dtso"
"${ORCHARD_PYTHON:-python3}" -m orchard_hardware.buildenv run \
  --bind "$headers:/headers:ro" --bind "$work:/out:rw" \
  --image localhost/orchard-hardware-kernel-toolchain:bookworm -- bash -euc '
    [[ $(fdtget -t s "$ORCHARD_OUT/base.dtb" / compatible) == "apple,j71s apple,s8000 apple,arm-platform" ]]
    [[ $(fdtget -t u "$ORCHARD_OUT/base.dtb" /soc "#address-cells") == 2 ]]
    [[ $(fdtget -t u "$ORCHARD_OUT/base.dtb" /soc "#size-cells") == 2 ]]
    if fdtget -t s "$ORCHARD_OUT/base.dtb" /soc/iommu@601008000 compatible >/dev/null 2>&1; then
      echo "DART0 already exists in base tree" >&2; exit 1
    fi
    clang-19 -E -P -x assembler-with-cpp -nostdinc -undef -D__DTS__ \
      -I "$ORCHARD_HEADERS" "$ORCHARD_OUT/dart.dtso" -o "$ORCHARD_OUT/dart.dts"
    dtc -@ -I dts -O dtb -o "$ORCHARD_OUT/dart.dtbo" "$ORCHARD_OUT/dart.dts"
    fdtoverlay -i "$ORCHARD_OUT/base.dtb" -o "$ORCHARD_OUT/result.dtb" "$ORCHARD_OUT/dart.dtbo"
    node=/soc/iommu@601008000
    [[ $(fdtget -t s "$ORCHARD_OUT/result.dtb" "$node" compatible) == "apple,s8000-dart apple,s5l8960x-dart" ]]
    [[ $(fdtget -t x "$ORCHARD_OUT/result.dtb" "$node" reg) == "6 1008000 0 4000" ]]
    [[ $(fdtget -t x "$ORCHARD_OUT/result.dtb" "$node" interrupts) == "0 f5 4" ]]
    [[ $(fdtget -t s "$ORCHARD_OUT/result.dtb" "$node" status) == okay ]]
    [[ -z $(fdtget -l "$ORCHARD_OUT/result.dtb" "$node") ]]
    domain=$(fdtget -t s "$ORCHARD_OUT/result.dtb" /__symbols__ ps_pcie)
    [[ $(fdtget -t x "$ORCHARD_OUT/result.dtb" "$domain" reg) == "80310 4" ]]
    [[ $(fdtget -t x "$ORCHARD_OUT/result.dtb" "$node" power-domains) == $(fdtget -t x "$ORCHARD_OUT/result.dtb" "$domain" phandle) ]]
    if fdtget -t s "$ORCHARD_OUT/result.dtb" /soc/pcie@610000000 compatible >/dev/null 2>&1; then
      echo "PCIe host already present; refusing isolated test" >&2; exit 1
    fi
    # Reject any IOMMU consumer, even on a disabled node: the experiment must
    # exercise DART probe alone and must not set up an endpoint DMA mapping.
    no_iommu_consumers() {
      local path=$1 child next
      if fdtget "$ORCHARD_OUT/result.dtb" "$path" iommus >/dev/null 2>&1 ||
         fdtget "$ORCHARD_OUT/result.dtb" "$path" iommu-map >/dev/null 2>&1; then
        echo "IOMMU consumer found at $path; refusing isolated test" >&2
        return 1
      fi
      for child in $(fdtget -l "$ORCHARD_OUT/result.dtb" "$path"); do
        if [[ "$path" == / ]]; then next="/$child"; else next="$path/$child"; fi
        no_iommu_consumers "$next" || return 1
      done
    }
    no_iommu_consumers /
  '
mkdir -p "$(dirname "$output")"
( set -o noclobber; cat "$work/result.dtb" > "$output" )
echo "DART0-only test tree: $output"
echo 'Booting powers PCIe and resets DART0; it may hang and require DFU recovery.'
