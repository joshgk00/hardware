set -eu
printf 'soc:j71s-pcie-diagnostic' > /sys/bus/platform/drivers/j71s-pcie-diagnostic/unbind
printf 'active-unbind=ok\n'
count=0
for device in /sys/bus/pci/devices/*; do [ -e "$device" ] && count=$((count+1)); done
printf 'pci-devices-after-unbind=%s\n' "$count"
dmesg | grep -E 'experimental PCI (hold|assignment)|rollback errors|restore errors' | tail -15
for f in capacity status current_now; do printf '%s=' "$f"; cat "/sys/class/power_supply/battery/$f"; done
