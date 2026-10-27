# J71s experimental device tree

The pinned kernel includes `s8000-j71s.dtb` for iPad 5 Wi-Fi with the S8000
chip. This recipe checks its compatible string and copies it as `j71s.dtb`.
It is the unmodified upstream tree: it does not provide touchscreen, internal
storage, or firmware support. It is not an installable release.

The J71s kernel configuration was used to boot an iPad6,11 / J71sAP into a
RAM-only BusyBox system with a framebuffer, GPIO buttons and USB serial/network.
The TSMC S8003 / J71t variant needs separate identification and validation.
