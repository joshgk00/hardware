#!/bin/sh
/bin/busybox --install -s /bin
set -eu
mount -t devtmpfs devtmpfs /dev
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t configfs configfs /sys/kernel/config
mkdir -p /sys/kernel/config/usb_gadget/test
cd /sys/kernel/config/usb_gadget/test || exit 1
echo 0x1d6b > idVendor
echo 0x0104 > idProduct
mkdir -p strings/0x409 configs/c.1/strings/0x409 functions/ncm.usb0
echo virtual-test > strings/0x409/serialnumber
echo isolated > strings/0x409/manufacturer
echo ncm-test > strings/0x409/product
echo ncm > configs/c.1/strings/0x409/configuration
ln -s "$PWD/functions/ncm.usb0" configs/c.1/ncm.usb0
for u in /sys/class/udc/*; do [ -e "$u" ] || continue; basename "$u" > UDC; break; done
sleep 3
echo VM_NCM_NETWORK_DEVICES
for p in /sys/class/net/*; do basename "$p"; done
echo VM_NCM_UDC
cat UDC
[ -n "$(cat UDC)" ] || { echo VM_UDC_MISSING; exec /bin/sh; }
gadget=$(cat functions/ncm.usb0/ifname)
host=
for p in /sys/class/net/*; do
 n=$(basename "$p")
 [ "$n" = "$gadget" ] && continue
 driver=$(readlink "$p/device/driver" 2>/dev/null || true)
 case "$driver" in */cdc_ncm) ;; *) continue ;; esac
 [ -z "$host" ] || { echo VM_MULTIPLE_HOST_INTERFACES; exec /bin/sh; }
 host=$n
done
[ -n "$host" ] || { echo VM_HOST_INTERFACE_MISSING; exec /bin/sh; }
unshare -n sleep 180 &
ns=$!
sleep 1
ip link set "$host" netns "$ns" || { echo VM_NETNS_MOVE_FAILED; kill "$ns"; exec /bin/sh; }
ip addr add 192.0.2.1/30 dev "$gadget"
ip link set "$gadget" up
nsenter -t "$ns" -n ip link set lo up
nsenter -t "$ns" -n ip addr add 192.0.2.2/30 dev "$host"
nsenter -t "$ns" -n ip link set "$host" up
sleep 2
if nsenter -t "$ns" -n ping -c 3 -W 2 192.0.2.1; then echo VM_NCM_PING_PASS; else echo VM_NCM_PING_FAIL; fi
fault=/sys/module/usb_f_ncm/parameters/test_force_busy
counter=/sys/module/usb_f_ncm/parameters/test_callback_count
if [ -w "$fault" ]; then
 if [ -r "$counter" ]; then before=$(cat "$counter"); else before=; fi
 echo 1 > "$fault"
 if nsenter -t "$ns" -n ping -c 1 -W 2 192.0.2.1; then echo VM_FAULT_PING_PASS; else echo VM_FAULT_PING_FAIL; fi
 if [ "$(cat "$fault")" = 0 ]; then echo VM_FAULT_CONSUMED; else echo VM_FAULT_NOT_CONSUMED; fi
 if [ -n "$before" ]; then after=$(cat "$counter"); printf 'VM_CALLBACK_DELTA %s\n' "$((after - before))"; fi
 busy=/sys/module/usb_f_ncm/parameters/test_busy_at
 next=/sys/module/usb_f_ncm/parameters/test_next_at
 if [ -r "$busy" ] && [ -r "$next" ]; then
  printf 'VM_BUSY_AT '; cat "$busy"
  printf 'VM_NEXT_AT '; cat "$next"
 fi
else
 echo VM_FAULT_HOOK_ABSENT
fi
kill "$ns"
echo VM_TEST_DONE
exec /bin/sh
