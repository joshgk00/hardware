#!/bin/sh
# Read the bound driver's command-status and stream-control registers; no writes.
set -eu
model=$(tr '\000' '\n' < /proc/device-tree/compatible | head -n 1)
[ "$model" = apple,j71s ] || { echo 'Wrong device tree' >&2; exit 1; }
node=/sys/bus/platform/devices/601008000.iommu
[ -L "$node/driver" ] || { echo 'DART0 driver not bound' >&2; exit 1; }
driver=$(readlink "$node/driver")
[ "${driver##*/}" = apple-dart ] || { echo 'Unexpected DART driver' >&2; exit 1; }
for i in 1 2 3; do
    reg=$(busybox devmem 0x601008000 32)
    printf 'sample=%s busy_bit=%s command_at_least_0x1000=%s status_bit12=%s\n' \
        "$i" "$(((reg >> 3) & 1))" "$((reg >= 4096))" "$(((reg >> 12) & 1))"
    [ "$i" = 3 ] || sleep 1
done
reg=$(busybox devmem 0x60100800c 32)
printf 'stream0_translation_enable_bit=%s\n' "$(((reg >> 7) & 1))"
