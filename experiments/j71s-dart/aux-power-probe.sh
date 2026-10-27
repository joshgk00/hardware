#!/bin/sh
# Report whether the AUX test device bound and whether DART responds; no writes.
set -eu
model=$(tr '\000' '\n' < /proc/device-tree/compatible | head -n 1)
[ "$model" = apple,j71s ] || { echo 'Wrong device tree' >&2; exit 1; }
for entry in aux:318 ref:148; do
    name=${entry%:*}
    offset=${entry#*:}
    node=/sys/bus/platform/devices/soc:j71s-pcie-$name-holder
    if [ -L "$node/driver" ]; then
        driver=$(readlink "$node/driver")
        printf '%s_holder_driver=%s\n' "$name" "${driver##*/}"
    else
        printf '%s_holder_driver=none\n' "$name"
    fi
    reg=$(busybox devmem "0x20e080$offset" 32)
    printf '%s_actual=%s target=%s all_ones=%s\n' "$name" "$(((reg >> 4) & 15))" "$((reg & 15))" "$((reg == 0xffffffff))"
done
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
