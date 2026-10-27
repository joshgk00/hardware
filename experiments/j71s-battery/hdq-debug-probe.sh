#!/bin/sh
# Run only on the diagnostic J71s RAM kernel after USB serial is ready.
set -eu
debug=/sys/kernel/debug
[ -d "$debug/dynamic_debug" ] || mount -t debugfs debugfs "$debug"
mount -o remount,rw "$debug"
cleanup() {
    echo 'func apple_serial_handle_irq -p' > "$debug/dynamic_debug/control" || true
    echo 'func w1_uart_hdq_xfer -p' > "$debug/dynamic_debug/control" || true
    mount -o remount,ro "$debug" || true
}
trap cleanup EXIT HUP INT TERM
echo 'func apple_serial_handle_irq +p' > "$debug/dynamic_debug/control"
echo 'func w1_uart_hdq_xfer +p' > "$debug/dynamic_debug/control"
# The gauge driver can cache errors for five seconds. Wait so this request
# actually initiates a new transfer while the probes are enabled.
sleep 6
cat /sys/class/power_supply/battery/capacity 2>/dev/null || true
dmesg | grep -E 'experimental UART IRQ status|experimental HDQ timeout' | tail -n 20 || true
cat /proc/tty/driver/s3c2410_serial
