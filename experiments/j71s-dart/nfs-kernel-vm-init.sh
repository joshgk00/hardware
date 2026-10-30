#!/bin/sh
# Disposable VM only: requires a scratch NFS export on host loopback port 32061.
set -eu
trap 'echo VM_NFS_TEST_FAILED; /busybox poweroff -f' EXIT
/busybox mkdir -p /proc /sys /dev /tmp /mnt /tmp/bin
/busybox mount -t proc proc /proc
/busybox mount -t sysfs sysfs /sys
/busybox mount -t devtmpfs devtmpfs /dev
/busybox --install -s /tmp/bin
export PATH=/tmp/bin:/usr/sbin:/usr/bin:/sbin:/bin
modprobe virtio_pci
modprobe virtio_net
modprobe nfs
modprobe nfsv4
ip link set lo up
ip link set eth0 up
ip addr add 10.0.2.15/24 dev eth0
ip route add default via 10.0.2.2
echo VM_NFS_MOUNT_START
timeout -s KILL 30 mount -t nfs4 -o vers=4.0,proto=tcp,port=32061,addr=10.0.2.2 10.0.2.2:/orchard-root /mnt
mkdir /mnt/kernel-vm-probe
printf 'kernel-client-proof\n' > /mnt/kernel-vm-probe/file
test "$(cat /mnt/kernel-vm-probe/file)" = kernel-client-proof
chmod 600 /mnt/kernel-vm-probe/file
ln /mnt/kernel-vm-probe/file /mnt/kernel-vm-probe/hard
ln -s file /mnt/kernel-vm-probe/sym
test "$(cat /mnt/kernel-vm-probe/sym)" = kernel-client-proof
mv /mnt/kernel-vm-probe/file /mnt/kernel-vm-probe/renamed
rm /mnt/kernel-vm-probe/sym /mnt/kernel-vm-probe/hard /mnt/kernel-vm-probe/renamed
rmdir /mnt/kernel-vm-probe
umount /mnt
echo VM_NFS_TEST_PASSED
trap - EXIT
poweroff -f
