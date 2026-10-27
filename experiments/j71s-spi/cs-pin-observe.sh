#!/bin/sh
# Read the Linux pinctrl driver's GPIO102 configuration register, no writes.
set -eu
model=$(tr '\000' '\n' < /proc/device-tree/compatible | head -n 1)
[ "$model" = apple,j71s ] || { echo 'Wrong device tree' >&2; exit 1; }
[ -d /sys/bus/platform/devices/20f100000.pinctrl ] || {
    echo 'Expected pin controller missing' >&2; exit 1;
}
# REG_GPIO(pin) is base + 4 * pin in pinctrl-apple-gpio.c.
reg=$(busybox devmem 0x20f100198 32)
printf 'GPIO102 peripheral_function=%s input_enabled=%s pull_code=%s\n' \
    "$(((reg >> 5) & 3))" "$(((reg >> 9) & 1))" "$(((reg >> 7) & 3))"
