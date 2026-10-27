#!/bin/sh
# Report whether the AUX test device bound and whether DART responds; no writes.
set -eu
model=$(tr '\000' '\n' < /proc/device-tree/compatible | head -n 1)
[ "$model" = apple,j71s ] || { echo 'Wrong device tree' >&2; exit 1; }
node=/sys/bus/platform/devices/soc:j71s-pcie-aux-holder
if [ -L "$node/driver" ]; then
    driver=$(readlink "$node/driver")
    printf 'aux_holder_driver=%s\n' "${driver##*/}"
else
    echo 'aux_holder_driver=none'
fi
reg=$(busybox devmem 0x20e080318 32)
printf 'aux_actual=%s target=%s all_ones=%s\n' "$(((reg >> 4) & 15))" "$((reg & 15))" "$((reg == 0xffffffff))"
dart=/sys/bus/platform/devices/601008000.iommu
if [ -L "$dart/driver" ]; then
    driver=$(readlink "$dart/driver")
    [ "${driver##*/}" = apple-dart ] || { echo 'Unexpected DART driver' >&2; exit 1; }
    for offset in 000 00c 020 024 030; do
        reg=$(busybox devmem "0x601008$offset" 32)
        printf 'dart_offset=%s all_ones=%s\n' "$offset" "$((reg == 0xffffffff))"
    done
else
    echo 'DART driver not bound; register reads skipped'
fi
echo 'Relevant boot messages:'
dmesg | grep -iE 'experimental DART0|pcie AUX power-domain holder|busy bit did not clear' | tail -n 20 || true
