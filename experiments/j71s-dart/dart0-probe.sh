#!/bin/sh
# Read-only diagnostics after an isolated DART0 boot; do not enumerate disks.
set -eu
model=$(tr '\000' '\n' < /proc/device-tree/compatible | head -n 1)
[ "$model" = apple,j71s ] || { echo 'Wrong device tree' >&2; exit 1; }
node=/sys/bus/platform/devices/601008000.iommu
if [ ! -d "$node" ]; then
    echo 'DART0 platform device not present'
elif [ ! -L "$node/driver" ]; then
    echo 'DART0 platform device present, no driver bound'
else
    driver=$(readlink "$node/driver")
    printf 'DART0 bound driver: %s\n' "${driver##*/}"
fi
echo 'DART-related kernel messages:'
dmesg | grep -iE '601008000|apple-dart|iommu' | tail -n 40 || true
echo 'Battery status:'
for field in status capacity current_now; do
    [ -r "/sys/class/power_supply/battery/$field" ] || continue
    printf '  %s: ' "$field"
    cat "/sys/class/power_supply/battery/$field" || true
done
