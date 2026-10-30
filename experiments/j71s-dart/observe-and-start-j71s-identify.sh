#!/bin/sh
# RAM-only, explicitly opt-in one-shot test. Captures non-identifying messages.
# Once armed, the test retains its resources until a physical reset.
set +e
if [ ! -r /dev/kmsg ]; then
 printf 'J71s Identify log stream unavailable; no command requested.\n'
 exit 1
fi
exec 3< /dev/kmsg || exit 1
# Allow for the diagnostic's 60-second start-gate wait as well as setup time.
# This remains a bounded observation, not a guarantee that every stage is seen.
busybox timeout 180 busybox cat <&3 | while IFS= read -r line; do
 case "$line" in
  *'translation fault:'*) printf 'DART translation fault detected (details remain on device)\n' ;;
  *'J71s Identify'*|*'TCB pre-init FIFO'*|*'TCB init experiment'*|*'TCB FIFO experiment'*|*'storage-port NVMMU fault'*) printf '%s\n' "$line" ;;
 esac
done &
observer=$!
sleep 1
gate=/sys/module/pcie_j71s_diagnostic/parameters/identify_start
if ! kill -0 "$observer" 2>/dev/null; then
 printf 'J71s Identify observer exited; no command requested.\n'
elif [ -w "$gate" ] && printf '1\n' > "$gate"; then
 printf 'J71s Identify observer attached; start gate enabled.\n'
else
 printf 'J71s Identify start gate unavailable; no command requested.\n'
fi
wait "$observer" || true
printf 'J71s Identify observation window ended; this does not confirm command completion.\n'
exec 3<&-
