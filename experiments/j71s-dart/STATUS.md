# iPad 5 J71s bring-up status

This is an experimental bring-up for the iPad 5 Wi-Fi J71s (`iPad6,11`,
S8000, DFU CPID `0x8000`, BDID `0x10`). It is not an installation guide and
should not be treated as production device support.

The related [J71t iPad 5 pull request](https://github.com/OrchardLinux/hardware/pull/6)
targets another iPad 5 variant with S8003 (CPID `0x8003`). Its driver code is a
useful reference, but it is not evidence that J71s works.

## What has been observed on this J71s

- A temporary Linux desktop was displayed, and touch responded to the user's
  test. This was running from RAM, not internal storage.
- A temporary PCI diagnostic enumerated the Apple NVMe endpoint and read its
  version with the controller and PCI bus mastering disabled.
- Linux attached the endpoint to a provisional DART domain and its software
  mappings matched the requested addresses. That is not evidence of physical
  DMA translation.
- The diagnostic allocated Identify buffers and prepared a translation
  descriptor with the controller disabled. The allocations and descriptor are
  retained for the one-shot session until physical reset.

The observer-gated Identify diagnostic has now been booted twice on J71s. In
both attempts the controller reported ready, and the last captured message was
emitted before the submission-doorbell write; the USB diagnostic connection
then disappeared. The second attempt added a short delay and further markers
around the write, but those later markers were not captured. No completion or
response was captured. Neither result establishes whether the doorbell write
completed or whether any physical DMA occurred. Omarchy is not installed, and
DMA isolation, reset behavior and translation retirement remain unverified.

## Next step

The controller-only comparison reached controller-ready and remained responsive
for approximately 10.4 seconds with the candidate host-link indicator up, without
a submission-doorbell write. This is not proof of successful DMA or storage.
Physically restart the iPad before the next diagnostic, because the controller
and buffers were left armed. A subsequent command-path test completed the same warmup but lost its USB
connection after the pre-submission marker, without a captured completion. This
does not establish whether the doorbell was written or DMA occurred. A later
physical comparison reached the same pre-submission link check and returned
successfully when it skipped the doorbell write; the controller was still armed,
so a physical reset is needed. A later command attempt captured the first
pre-doorbell link-up marker but lost USB before a doorbell-return marker; the
final check and write cannot be confirmed from the log. A matched no-write
comparison subsequently survived the same wait and final check, then recorded
that it skipped the write; this is suggestive but does not prove the cause.
A successful Identify
response would still not prove reliable storage or a safe installer.

Device-specific captures, boot artifacts, serial output and generated Apple
Device Tree material are kept private. Do not commit them to a public branch.
The detailed experiment history, candidate patches, limitations, and host tests
are in [README.md](README.md).

The pre-init FIFO guard was physically exercised in no-doorbell mode. It saw a valid status with the candidate empty bit set and the diagnostic returned successfully after skipping the doorbell. This does not establish working DMA or explain the command-path disconnects. Physical reset is required after the test.

[Hardware PR 30](https://github.com/OrchardLinux/hardware/pull/30) adds an experimental USB NFS-root boot, physically demonstrated on an iPhone 6. It may provide a parallel route to a writable host-served Omarchy system while J71s internal storage is investigated. The J71s path is untested; it needs a matching kernel with NFS, a suitable server and an ownership-preserving root. Our previous J71s USB desktop and read-only Omarchy image are relevant foundations, not proof that this NFS path works.

A separate NFS-capable kernel and its modules were built using the previously tested J71s touch source, and the matching module tree was installed into the private root. The verified Omarchy archive was extracted into a private rootless user namespace; root and systemd appeared as 0:0 there, and the tablet home as 1000:1000. A loopback-only rootless Ganesha/VFS probe started, but a userspace NFSv4 client received `NFS4ERR_PERM`; server debug logged `open_by_handle` failing with `EPERM`. The server was stopped. This server setup is therefore not ready for device use; privileged export access or a different server backend must be validated, and the private root must not be treated as a verified running system.

An alternative userspace NFSv4 server ([neilpang/nfsd](https://github.com/neilpang/nfsd), source `b9ac075`) was built and its nine unit tests passed in a separate container. In a loopback-only disposable export, a separate libnfs client listed and read files, wrote a root-owned file and a UID/GID 1000 file, and read them back. A nested `/orchard-root` path matching Orchard's staging requirements also worked. The server was stopped after testing. These are local smoke tests, not Linux-kernel mount, full systemd filesystem semantics, security review, or a J71s boot; its in-memory handles and restart behavior need consideration. No third-party code was added to this branch.

The private Omarchy root was staged with a J71s NFS identity receipt and a RAM startup configured for the previously tested USB NCM subnet and manual handoff. A loopback-only, read-only test of the real root returned matching receipt and systemd file hashes through NFS. A first container mapping exposed the root group as 1000; setting both container UID and GID mappings to 0 corrected the client view to systemd 0:0 and tablet home 1000:1000. The server was stopped. ARM BusyBox applets required by the runtime were present under user-mode emulation, but actual NFS mounting and full root handoff are untested. The separate kernel build explicitly verifies that the NFS configuration survives `olddefconfig`.

The private NFS test copy of the J71b Omarchy root had a getty dependency on a J71b-specific hardware guard and an enabled J71b charging lease. `prepare-nfs-test-root.py` replaces that getty dependency with a J71s-only guard requiring the matching kernel release, `apple,j71s`, successful NFS handoff and an NFS root; it disables the J71b charging lease in that copy and preserves the original getty drop-in. It was exercised on a disposable fixture and applied to the private test root, but has not been boot-tested. This does not provide J71s charging support or modify the original archive.

A private NFS RAM startup was staged with the previously verified J71s touch firmware and calibration from the device-specific stage-3 diagnostic image. Its initramfs archive contains the USB, NFS validation and handoff scripts, ARM BusyBox and those private firmware files. The original stage-3 image manifest was verified before extraction. A private image has now been assembled with the separately built NFS kernel and verified component hashes; it has not been boot-tested. The existing BusyBox applets were checked under ARM userspace emulation; NFS mount behavior on the iPad remains untested.

The loopback NFS client wrote and read temporary files in the private Omarchy test root as UID/GID 0 and 1000; ownership was correct. In a separate disposable export, a UID 1000 client was denied a root-owned mode-0600 file that UID 0 could read. Both servers were stopped and their probe files removed. This is narrow functionality evidence, not a security review or proof of all file permission behavior.

The assembled kernel's configuration enables NFSv4, NCM, ACM, simpledrm and the N1 touch driver as built-ins. Its linked symbol map contains the NFSv4 filesystem, NCM and ACM bind functions, simpledrm driver and N1 driver. This checks that the components survived the build, not that they initialize or work together on the iPad.

An additional libnfs NFSv4 loopback test on a disposable export exercised mkdir, create, write, chmod, hard link, symbolic link/readlink, rename and cleanup. An immediate write after `nfs_creat` failed with `NFS4ERR_OPENMODE`. Inspection of [libnfs 4.0.0 source](https://github.com/sahlberg/libnfs/blob/030814506e529ef1f1572c7b6e3fc2e4c10cb544/lib/libnfs-sync.c#L938) found `nfs_creat` passes zero flags; the NFSv4 open code treats those as read access. A repeat with `nfs_create` and `O_WRONLY` wrote successfully without reopening and all other listed operations passed. This explains the tested failure as a client open-mode choice; it does not validate Linux-kernel-client behavior. The probe is `nfs-ops-probe.c` and must only be run against a disposable loopback export.

A disposable x86-64 Debian 6.1 Linux VM subsequently mounted the loopback-only userspace NFS export using the kernel NFSv4.0 client and BusyBox, then created and read a file, changed its mode, created hard and symbolic links, renamed and removed the test files, and unmounted successfully. The server was stopped and the scratch directory was confirmed removed. This validates that limited kernel-client sequence, not the ARM kernel, systemd handoff, the full Omarchy filesystem, or J71s hardware. The VM init script is `nfs-kernel-vm-init.sh`.

A second disposable Linux VM mounted the actual private Omarchy test root read-only over NFSv4.0. Through the kernel client it verified the receipt digest, AArch64 systemd ELF header, root ownership and mode of systemd, tablet UID/GID, and ownership of the matching kernel module index. It then unmounted and shut down, and the server was stopped. This is stronger than the user-space client check but does not boot systemd or exercise the iPad's ARM kernel or USB network.

A separate emulator-only ARM64 build from the J71s NFS kernel source, retaining 16 KiB pages and NFS while adding virtual serial and network drivers, booted under QEMU TCG. Using the same staged ARM BusyBox, it mounted the private Omarchy root read-only over NFSv4.0 and verified the receipt digest, systemd ownership, tablet ownership and module index; it unmounted and shut down, and the server was stopped. The first emulator run used a Cortex-A72 model without the required 16 KiB translation granule and produced no console; a Cortex-A76 model booted successfully. This exercises ARM NFS with a modified kernel configuration, not J71s hardware, USB gadget operation, or systemd handoff.

A disposable copy-on-write Omarchy root was booted in the ARM64 16 KiB QEMU variant over a loopback-only writable NFSv4.0 export. A VM-specific init moved the virtual filesystems and handed PID 1 to the image's AArch64 systemd; a minimal temporary systemd target confirmed PID 1, wrote and read a file on the NFS root, removed it and shut down. The server was stopped and the proof file was absent afterward. The iPad's prepared root was not used for that write. `nfs-arm-systemd-vm-init.sh` records the VM-only procedure. This is not a normal desktop boot, does not test the original USB startup path or J71s hardware, and does not establish full NFS or systemd compatibility.

A further ARM64 16 KiB QEMU test booted the disposable NFS root through the normal `multi-user.target` and a temporary observation target confirmed that it was active, then wrote, read and removed a test file. QEMU's user network used restricted mode with only a loopback NFS port forwarded. The virtual NIC was marked unmanaged to preserve the NFS connection, and the iPad's physical tty1 login was masked in the VM copy because virtual hardware cannot meet the J71s guard. The server was stopped and the probe file was removed; the real test root was not used for the write. `nfs-arm-multi-vm-init.sh` captures the VM-only startup. This is not a desktop or physical iPad test, and does not prove every service was healthy.

An ARM QEMU VM using a separate copy of the NFS root, virtual DRM/input, and a virtual-board-specific version of the startup guard reached multi-user startup and observed a `labwc` process under UID 1000. Two virtual display captures were black, so no usable graphical desktop was demonstrated. The VM shut down and its loopback server was stopped. This does not establish iPad display or touch behavior and needs further diagnosis before claiming a working desktop. A further run forced modern virtio-mmio, allowing the virtual GPU and input drivers to bind; `labwc` was observed running, but a capture remained black. Its log reported that Xwayland was unavailable and that it continued without Xwayland. This remains an incomplete virtual desktop test, not evidence of a physical display regression.

A repeat of the virtual desktop run captured the compositor's stderr in the disposable VM copy. It reported that no GPUs were found and it could not create a DRM backend. The earlier process check only observed a transient `labwc` process, so it must not be interpreted as a running desktop. The cause of the missing virtual GPU is still under investigation and does not establish a failure of the iPad's physical display.

## Upstream integration update

The related J71t work was merged in [hardware PR 28](https://github.com/OrchardLinux/hardware/pull/28). Its author reported RAM-booted read-only storage, display, touch and Wi-Fi tests on S8003 J71t; installation was not tested and remains disabled. Upstream main at `ae1457e` still marks S8000 J71s storage and Wi-Fi unsupported. The J71t results are valuable comparisons, not a validation of this J71s hardware or our pending FIFO test. The new main also includes an independently validated T7000 host sequence; similarity does not establish S8000 compatibility.

## Contributions already opened

- [Fix packed S5L DART stream controls](https://github.com/OrchardLinux/linux/pull/1)
  was closed after its locking issue was incorporated into the hardware
  repository's [upstream patch](https://github.com/OrchardLinux/hardware/commit/f82f35a396d314bd815a2f44e01727993e30cc21),
  with Josh credited. The upstream fix was tested on an iPad 6, not this J71s.
- [Select the host Rust installer architecture](https://github.com/OrchardLinux/hardware/pull/13)
  is a draft hardware PR; it fixes a build-host issue, not iPad support.

The broader J71s storage and device support in this experiment branch is not
ready to claim as a working upstream contribution. Preserve tested findings and
separate independently reviewable changes when their hardware behavior is known.

The USB NFS image, root receipt and module index agree on the J71s profile and
kernel release. A local selector identifies its rescue serial by product and
staged root UUID and the physical USB location recorded at DFU, and finds the
network interface under that same USB device;
synthetic tests reject wrong or ambiguous identities. This is a convenience
check, not the ECID-bound recovery identity protocol. The device still needs a
physical reset before this RAM image can be booted.

Offline ARM userspace emulation also exercised the staged BusyBox `stat -c`,
`sha256sum`, `od -An -v -tx1`, `awk`, `timeout -s KILL`, and `ip link/address`
syntax used by the NFS runtime. Actual NFS mounting still requires a device
boot and remains unverified.

While the no-doorbell diagnostic was still running, its battery interface
reported 84% and discharging, with `current_now=-566000` microamps and
`voltage_now=4052000` microvolts. This is one software reading, not a measured
charger current or a reliable runtime estimate. The armed controller still
requires a physical reset before another boot.

The earlier USB diagnostic links its ACM function before NCM; the new NFS
startup links NCM before ACM. Linux interface names can therefore differ, so
the old manually configured `j71s-ram-transfer` profile must not be applied
blindly. It has autoconnect disabled and was not active when checked. The NFS
selector instead finds the interface under the same selected USB device. For
the physical test, use a temporary NetworkManager profile bound to that
verified interface, with the isolated /30 and no default route, and remove it
afterward. This setup has not yet been exercised on the iPad.

During the no-doorbell diagnostic, a later read-only check at approximately
47 minutes of uptime found no matching DART translation-fault, storage-port
NVMMU-fault, or kernel-panic lines in the currently retained kernel log. The
battery interface reported 84% and discharging. This is an idle observation;
the ring buffer may have overwritten earlier messages, and it does not prove
working command execution or physical DMA. Resources remain armed until a
physical reset.

A physical J71s test booted the prepared RAM image, reached its USB rescue shell, and successfully mounted and validated the NFS root read-only. Following the manual handoff, the rescue console reported PID 1 as `systemd`, the root filesystem as read-write NFSv4.0, and handoff state `ready`. The user observed ongoing systemd boot messages. During startup the kernel repeatedly reported the NFS server not responding and later recovering; host pings also showed substantial packet loss. A usable desktop and stable operation have not been verified. This is an experimental host-served root, not working internal storage.

The physical NFS server later logged expired client leases after the connection stalled, and the iPad logged journal-service watchdog failure during startup. A proposed [upstream NCM timer fix](https://patchew.org/linux/20260727165441.1969927-1-flavra@baylibre.com/) describes transmit stalls under sustained traffic. The tested J71s kernel lacks that change. A separate kernel with the proposed patch built successfully, but has not been booted or validated; it is a lead, not proof of the cause or a fix.
