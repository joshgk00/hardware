#!/bin/sh
# Run only in the experimental RAM boot; inspect public battery status and
# relevant kernel messages. Never dump device-tree properties or calibration.
set -eu
echo '=== battery-related kernel messages ==='
dmesg | grep -iE '20a0d4000|s5l-uart|hdq|bq27|onewire|w1_master|battery' | tail -n 100 || true
echo '=== power supplies ==='
for supply in /sys/class/power_supply/*; do
    [ -e "$supply" ] || continue
    printf '%s\n' "${supply##*/}"
    for field in type status capacity voltage_now current_now temp; do
        if [ -r "$supply/$field" ]; then
            printf '  %s: ' "$field"
            cat "$supply/$field" || true
        fi
    done
done
echo '=== serial and one-wire devices ==='
for entry in /sys/bus/serdev/devices/* /sys/bus/w1/devices/*; do
    [ -e "$entry" ] && printf '%s\n' "$entry"
done
true
