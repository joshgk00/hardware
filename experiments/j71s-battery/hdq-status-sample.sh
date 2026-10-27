#!/bin/sh
# Read the UART status/FIFO registers already read by the Linux UART driver.
# Experimental J71s RAM boot only; do not write registers or read FIFO data.
set -eu
model=$(tr '\000' '\n' < /proc/device-tree/compatible | head -n 1)
[ "$model" = apple,j71s ] || { echo 'Wrong device tree' >&2; exit 1; }
[ -L /sys/bus/platform/devices/20a0d4000.serial/driver ] || { echo 'UART driver not bound' >&2; exit 1; }
[ -r /sys/class/power_supply/battery/capacity ] || { echo 'Battery device missing' >&2; exit 1; }
sleep 6 # Expire the gauge driver's five-second cache.
cat /sys/class/power_supply/battery/capacity >/dev/null 2>&1 &
request=$!
i=0 ready=0 rx_fifo=0 tx_fifo=0
while [ "$i" -lt 300 ]; do
    status=$(busybox devmem 0x20a0d4010 32)
    fifo=$(busybox devmem 0x20a0d4018 32)
    [ $((status & 1)) -eq 0 ] || ready=$((ready + 1))
    # Masks are the values used by the current S5L Linux UART driver.
    [ $((fifo & 0x10f)) -eq 0 ] || rx_fifo=$((rx_fifo + 1))
    [ $((fifo & 0x2f0)) -eq 0 ] || tx_fifo=$((tx_fifo + 1))
    i=$((i + 1))
done
wait "$request" || true
printf 'Samples=%s RX-ready=%s RX-FIFO=%s TX-FIFO=%s\n' "$i" "$ready" "$rx_fifo" "$tx_fifo"
