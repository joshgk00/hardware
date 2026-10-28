#!/bin/sh
# Run inside the experimental RAM boot after the user is ready to tap.
# Captures at most 512 input_event records or 20 seconds, then prints a compact
# event stream. This only reads the input device and writes to RAM /tmp.
set -eu
node=''
for name in /sys/class/input/event*/device/name; do
    [ -r "$name" ] || continue
    [ "$(cat "$name")" = 'Apple N1 Touchscreen' ] || continue
    event=${name#/sys/class/input/}
    event=${event%%/*}
    [ -z "$node" ] || { echo 'Ambiguous N1 input devices'; exit 1; }
    node=/dev/input/$event
done
[ -n "$node" ] && [ -c "$node" ] || { echo 'N1 input device unavailable'; exit 1; }
printf 'Capturing touchscreen events from %s for up to 20 seconds.\n' "$node"
: > /tmp/j71s-touch-events.bin
timeout 20 dd if="$node" of=/tmp/j71s-touch-events.bin bs=24 count=512 2>/dev/null || status=$?
[ "${status:-0}" -eq 0 ] || [ "${status:-0}" -eq 124 ] || [ "${status:-0}" -eq 143 ] || { echo 'Input capture failed'; exit 1; }
printf 'Captured bytes: '
wc -c < /tmp/j71s-touch-events.bin
printf 'Event data (base64):\n'
base64 /tmp/j71s-touch-events.bin
