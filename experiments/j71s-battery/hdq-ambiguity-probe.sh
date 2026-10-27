#!/bin/sh
# Run only on the diagnostic J71s RAM kernel. This reports counts, not raw
# gauge bytes, and does not change the driver's decoding or gauge settings.
set -eu
model=$(tr '\000' '\n' < /proc/device-tree/compatible | head -n 1)
[ "$model" = apple,j71s ] || { echo 'Wrong device tree' >&2; exit 1; }
debug=/sys/kernel/debug
[ -d "$debug/dynamic_debug" ] || mount -t debugfs debugfs "$debug"
mount -o remount,rw "$debug"
cleanup() {
    echo 'func w1_uart_hdq_xfer -p' > "$debug/dynamic_debug/control" || true
    mount -o remount,ro "$debug" || true
}
trap cleanup EXIT HUP INT TERM
grep -q 'experimental HDQ ambiguous response symbols' "$debug/dynamic_debug/control" || {
    echo 'Ambiguity diagnostic kernel is not running' >&2; exit 1;
}
echo 'func w1_uart_hdq_xfer +p' > "$debug/dynamic_debug/control"
sleep 6 # The gauge driver can cache results for five seconds.
cat /sys/class/power_supply/battery/capacity >/dev/null 2>&1 || true
dmesg | grep -F 'experimental HDQ ambiguous response symbols=' | tail -n 30 || true
