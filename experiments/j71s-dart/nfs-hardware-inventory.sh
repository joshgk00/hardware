#!/bin/sh
# Read-only inventory for the Orchard NFS rescue shell; does not prove function.
B=/run/orchard/rescue/busybox
printf 'BATTERY '; "$B" cat /sys/class/power_supply/battery/capacity 2>/dev/null || true
for class in sound iio/devices bluetooth backlight drm nvme net; do
    printf 'CLASS %s\n' "$class"
    base=/sys/class/$class
    [ "$class" = iio/devices ] && base=/sys/bus/iio/devices
    for path in "$base"/*; do
        [ -e "$path" ] || continue
        name=${path##*/}
        case "$class:$name" in net:lo) continue;; esac
        printf '  %s' "$name"
        if [ "$class" = iio/devices ] && [ -r "$path/name" ]; then
            printf ' '; "$B" cat "$path/name"
        else
            printf '\n'
        fi
    done
done
printf 'SYSTEM '; "$B" timeout -s KILL 10 /usr/bin/systemctl is-system-running || true
