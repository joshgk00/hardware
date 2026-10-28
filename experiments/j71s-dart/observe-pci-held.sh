for i in $(seq 1 25); do
  found=0
  for device in /sys/bus/pci/devices/*; do
    [ -f "$device/vendor" ] || continue
    vendor=$(cat "$device/vendor"); product=$(cat "$device/device")
    if [ "$vendor" = 0x106b ] && [ "$product" = 0x2002 ]; then
      printf 'endpoint-visible=1\n'
      printf 'endpoint-driver='; if [ -L "$device/driver" ]; then echo bound; else echo none; fi
      printf 'endpoint-bar0='; head -n 1 "$device/resource"
      found=1; break
    fi
  done
  [ "$found" = 1 ] && break
  sleep 1
done
[ "$found" = 1 ] || echo 'endpoint-visible=0'
sleep 22
count=0
for device in /sys/bus/pci/devices/*; do [ -e "$device" ] && count=$((count + 1)); done
printf 'pci-devices-after-window=%s\n' "$count"
dmesg | grep -E 'experimental PCI (hold|scan|assignment|iomap)|rollback errors|restore errors' | tail -30
for f in capacity status current_now; do printf '%s=' "$f"; cat "/sys/class/power_supply/battery/$f"; done
