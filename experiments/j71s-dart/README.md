# Experimental older Apple DART stream fix

At Hoolock kernel revision `6831bc701a6ce059e71e5aaa9488c9195bea6927`,
`apple_dart_s5l8960x_write_tcr()` reads a shared register containing four
8-bit stream fields. Its read function shifts the requested field, but the
write function retains only the selected old field and ORs the new value into
the low byte. This can clear unrelated streams, retain bits intended to be
cleared, and update the wrong field for streams 1–3.

`fix-s5l-tcr-stream.patch` replaces only the selected field and rejects an
out-of-range stream or value. `test-tcr.py` extracts the actual patched C
function and executes it with a mocked register; it checks enabling and
disabling each stream, preservation of other fields, and no writes for invalid
arguments. It requires a host C compiler and a separately patched kernel tree.

The J71s Apple tree identifies a 4 KiB-page S8000 PCIe DART; the kernel's
older DART variant also uses 4 KiB pages. This similarity does not establish
that the driver works on S8000. The patch has not been tested on a physical
DART, does not enable a device tree node, and does not establish why another
device hung during DART probe. Do not use it to access internal storage until
the controller, DMA and recovery path have been separately validated.
