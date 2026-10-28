set -eu
driver=/sys/bus/platform/drivers/j71s-pcie-diagnostic
node=soc:j71s-pcie-diagnostic
printf '%s' "$node" > "$driver/unbind"
printf 'initial-unbind=ok\n'
printf '%s' "$node" > "$driver/bind"
printf 'rebind=ok\n'
found=0
for i in $(seq 1 20); do
  for device in /sys/bus/pci/devices/*; do
    [ -f "$device/vendor" ] || continue
    if [ "$(cat "$device/vendor")" = 0x106b ] && [ "$(cat "$device/device")" = 0x2002 ]; then found=1; break; fi
  done
  [ "$found" = 1 ] && break
  sleep 1
done
printf 'endpoint-before-unbind=%s\n' "$found"
[ "$found" = 1 ] || exit 1
before=$(date +%s)
printf '%s' "$node" > "$driver/unbind"
after=$(date +%s)
printf 'active-unbind=ok elapsed-seconds=%s\n' "$((after-before))"
count=0
for device in /sys/bus/pci/devices/*; do [ -e "$device" ] && count=$((count + 1)); done
printf 'pci-devices-after-unbind=%s\n' "$count"
dmesg | grep -E 'experimental PCI (hold|assignment)|rollback errors|restore errors' | tail -22
for f in capacity status current_now; do printf '%s=' "$f"; cat "/sys/class/power_supply/battery/$f"; done
