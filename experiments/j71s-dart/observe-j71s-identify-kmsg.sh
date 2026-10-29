#!/bin/sh
# RAM diagnostic only. Stream a bounded set of non-identifying kernel messages.
# /dev/kmsg may stop producing output if the device stalls; the host should
# retain any partial serial output rather than assuming the test finished.
set +e
busybox timeout 50 busybox cat /dev/kmsg | while IFS= read -r line; do
 case "$line" in
  *'translation fault:'*) printf 'DART translation fault detected (details remain on device)\n' ;;
  *'J71s Identify'*|*'TCB init experiment'*|*'TCB FIFO experiment'*|*'storage-port NVMMU fault'*) printf '%s\n' "$line" ;;
 esac
done
