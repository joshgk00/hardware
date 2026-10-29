#!/bin/sh
# RAM-only, explicitly opt-in one-shot test. Captures non-identifying messages.
# Once armed, the test retains its resources until a physical reset.
set +e
if [ ! -r /dev/kmsg ]; then
 printf 'J71s Identify log stream unavailable; no command requested.\n'
 exit 1
fi
exec 3< /dev/kmsg || exit 1
busybox timeout 50 busybox cat <&3 | while IFS= read -r line; do
 case "$line" in
  *'translation fault:'*) printf 'DART translation fault detected (details remain on device)\n' ;;
  *'J71s Identify'*|*'TCB init experiment'*|*'TCB FIFO experiment'*|*'storage-port NVMMU fault'*) printf '%s\n' "$line" ;;
 esac
done &
observer=$!
sleep 1
gate=/sys/module/pcie_j71s_diagnostic/parameters/identify_start
if [ -w "$gate" ] && printf '1\n' > "$gate"; then
 printf 'J71s Identify observer attached; start gate enabled.\n'
else
 printf 'J71s Identify start gate unavailable; no command requested.\n'
fi
wait "$observer" || true
exec 3<&-
