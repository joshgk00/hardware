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

No NVMe command or physical storage DMA has been confirmed, and Omarchy is not
installed. The one-shot Identify implementation and its opt-in boot image are
experimental and have not been run on the iPad. The candidate's host and device
DMA isolation, reset behavior and translation retirement remain unverified.

## Next step

Physically restart the iPad to clear the previous one-shot session. Once it is
connected and its battery level is checked, a DFU boot can test the candidate
that attempts one read-only Identify command. Capture the stage messages and
retain all buffers until another physical reset, even after a timeout. A response
is only a first hardware result; it does not establish reliable storage or a
safe installer.

Device-specific captures, boot artifacts, serial output and generated Apple
Device Tree material are kept private. Do not commit them to a public branch.
The detailed experiment history, candidate patches, limitations, and host tests
are in [README.md](README.md).

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
