set -eu
find_endpoint() {
 for device in /sys/bus/pci/devices/*; do
  [ -f "$device/vendor" ] || continue
  if [ "$(cat "$device/vendor")" = 0x106b ] && [ "$(cat "$device/device")" = 0x2002 ]; then echo "$device"; return 0; fi
 done
 return 1
}
for i in $(seq 1 20); do endpoint=$(find_endpoint) && break; sleep 1; done
[ -n "${endpoint:-}" ]
printf 'initial-endpoint=visible\n'
printf 'initial-driver='; if [ -L "$endpoint/driver" ]; then echo bound; else echo none; fi
sleep 25
endpoint=$(find_endpoint)
printf 'after-25-seconds=visible\n'
printf 'after-driver='; if [ -L "$endpoint/driver" ]; then echo bound; else echo none; fi
printf 'bar0='; head -n 1 "$endpoint/resource"
dmesg | grep -E 'experimental PCI (hold|assignment|iomap)' | tail -10
for f in capacity status current_now; do printf '%s=' "$f"; cat "/sys/class/power_supply/battery/$f"; done
