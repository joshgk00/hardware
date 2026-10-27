#!/bin/sh
# Read-only check after the controller-only experimental RAM boot.
set -eu
model=$(tr '\000' '\n' < /proc/device-tree/compatible | head -n 1)
[ "$model" = apple,j71s ] || { echo 'Wrong device tree' >&2; exit 1; }
node=/sys/bus/platform/devices/20a08c000.spi
if [ ! -d "$node" ]; then
    echo 'SPI3 platform device not present'
elif [ ! -L "$node/driver" ]; then
    echo 'SPI3 platform device present, no driver bound'
else
    driver=$(readlink "$node/driver")
    printf 'SPI3 bound driver: %s\n' "${driver##*/}"
fi
echo 'SPI master devices:'
for dev in /sys/class/spi_master/*; do
    [ -e "$dev" ] && printf '  %s\n' "${dev##*/}"
done
echo 'SPI-related kernel messages:'
dmesg | grep -iE '20a08c000|spi-apple|apple-spi' | tail -n 40 || true
echo 'Battery status:'
for field in status capacity current_now; do
    [ -r "/sys/class/power_supply/battery/$field" ] || continue
    printf '  %s: ' "$field"
    cat "/sys/class/power_supply/battery/$field" || true
done
