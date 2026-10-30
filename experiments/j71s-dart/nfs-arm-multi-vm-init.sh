#!/bin/busybox sh
# Disposable VM only; requires an isolated scratch NFS root and guest forwarding.
set -eu
trap 'echo ARM_SYSTEMD_PREP_FAILED; /bin/busybox poweroff -f' EXIT
/bin/busybox --install -s /bin
export PATH=/bin:/sbin:/usr/bin:/usr/sbin
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev
mount -t tmpfs -o mode=0755 tmpfs /run
mkdir -p /dev/pts /run/systemd/system
mount -t devpts -o mode=0620,ptmxmode=0666 devpts /dev/pts
ip link set lo up
ip link set eth0 up
ip addr add 10.0.2.15/24 dev eth0
ip route add default via 10.0.2.2
echo ARM_SYSTEMD_MOUNT_START
timeout -s KILL 90 mount -t nfs4 -o vers=4.0,proto=tcp,port=32061,addr=10.0.2.10 10.0.2.10:/orchard-root /mnt
test -x /mnt/usr/lib/systemd/systemd
cp /bin/busybox /run/busybox
mkdir -p /run/NetworkManager/conf.d
cat > /run/NetworkManager/conf.d/90-vm-nfs.conf <<'NETWORK'
[keyfile]
unmanaged-devices=interface-name:eth0
NETWORK
cat > /run/systemd/system/vm-multi-probe.target <<'UNIT'
[Unit]
Description=Disposable ARM NFS multi-user probe
DefaultDependencies=no
Requires=multi-user.target vm-multi-probe.service
After=multi-user.target vm-multi-probe.service
AllowIsolate=yes
UNIT
cat > /run/systemd/system/vm-multi-probe.service <<'UNIT'
[Unit]
Description=Observe ARM NFS multi-user startup
After=multi-user.target
Requires=multi-user.target
[Service]
Type=oneshot
ExecStart=/usr/bin/bash /run/vm-probe.sh
StandardOutput=journal+console
StandardError=journal+console
UNIT
cat > /run/vm-probe.sh <<'PROBE'
#!/usr/bin/bash
set -eu
trap 'echo ARM_MULTI_TEST_FAILED > /dev/console; /run/busybox poweroff -f' EXIT
test "$(cat /proc/1/comm)" = systemd
test "$(uname -m)" = aarch64
systemctl is-active multi-user.target > /dev/console
systemctl --failed --no-legend --no-pager --plain > /dev/console || true
test ! -e /var/tmp/j71s-vm-multi-proof
printf 'arm-multi-proof\n' > /var/tmp/j71s-vm-multi-proof
test "$(cat /var/tmp/j71s-vm-multi-proof)" = arm-multi-proof
rm /var/tmp/j71s-vm-multi-proof
echo ARM_MULTI_TEST_PASSED > /dev/console
trap - EXIT
/run/busybox poweroff -f
PROBE
chmod 755 /run/vm-probe.sh
for n in dev proc sys run; do mount --move "/$n" "/mnt/$n"; done
trap - EXIT
exec /bin/busybox switch_root /mnt /usr/lib/systemd/systemd
