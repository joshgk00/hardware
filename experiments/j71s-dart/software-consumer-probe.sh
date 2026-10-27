#!/bin/sh
# Read-only observations after a software-only DART consumer boot.
set -eu
model=$(tr '\000' '\n' < /proc/device-tree/compatible | head -n 1)
[ "$model" = apple,j71s ] || { echo 'Wrong device tree' >&2; exit 1; }
echo 'Software consumer platform devices:'
for node in /sys/bus/platform/devices/*j71s-dart-software-consumer*; do
    [ -e "$node" ] || continue
    printf '  %s' "${node##*/}"
    if [ -L "$node/driver" ]; then
        driver=$(readlink "$node/driver")
        printf ' driver=%s' "${driver##*/}"
    else
        printf ' driver=none'
    fi
    [ ! -L "$node/iommu_group" ] || printf ' iommu_group=present'
    printf '\n'
done
echo 'DART and consumer messages:'
dmesg | grep -iE '601008000|apple-dart|j71s-dart|iommu' | tail -n 60 || true
echo 'Battery status:'
for field in status capacity current_now; do
    [ -r "/sys/class/power_supply/battery/$field" ] || continue
    printf '  %s: ' "$field"
    cat "/sys/class/power_supply/battery/$field" || true
done
