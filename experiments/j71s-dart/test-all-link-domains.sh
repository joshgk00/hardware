#!/bin/sh
# Validate a locally supplied J71s diagnostic tree without booting it.
set -eu
if [ "$#" -ne 1 ]; then
  echo "Usage: $0 J71S_DIAGNOSTIC_DTB" >&2
  exit 2
fi
base=$1
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT HUP INT TERM
[ "$(fdtget -t s "$base" / compatible)" = 'apple,j71s apple,s8000 apple,arm-platform' ]
dtc -@ -I dts -O dtb -o "$tmp/all-links.dtbo" "$here/j71s-all-link-domains.dtso"
fdtoverlay -i "$base" -o "$tmp/result.dtb" "$tmp/all-links.dtbo"
dtb=$tmp/result.dtb
node=/soc/iommu@601008000
props=$(fdtget -p "$dtb" "$node")
printf '%s\n' "$props" | grep -qx 'orchard,early-power-test'
printf '%s\n' "$props" | grep -qx 'orchard,shared-bits-test'
expected=''
for sym in ps_pcie ps_pcie_aux ps_pcie_ref ps_pcie_link0 ps_pcie_link1 ps_pcie_link2 ps_pcie_link3; do
  path=$(fdtget -t s "$dtb" /__symbols__ "$sym")
  phandle=$(fdtget -t x "$dtb" "$path" phandle)
  expected="${expected:+$expected }$phandle"
  case "$sym" in
    ps_pcie_link1|ps_pcie_link2|ps_pcie_link3)
      if fdtget "$dtb" "$path" apple,min-state >/dev/null 2>&1; then
        echo "Unexpected minimum state on $sym" >&2; exit 1
      fi ;;
  esac
done
[ "$(fdtget -t x "$dtb" "$node" power-domains)" = "$expected" ]
echo 'Seven-domain diagnostic overlay validation passed.'
