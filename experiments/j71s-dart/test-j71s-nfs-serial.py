#!/usr/bin/env python3
"""Exercise NFS serial selection with synthetic sysfs identities."""
from pathlib import Path
from tempfile import TemporaryDirectory
from j71s_nfs_serial import find_nfs_serial

root = '00000000-0000-4000-8000-000000000001'
boot = '00000000-0000-4000-8000-000000000002'
with TemporaryDirectory() as temporary:
    sys = Path(temporary) / 'sys'
    dev = Path(temporary) / 'dev'
    usb = sys / 'devices/usb/test'
    usb.mkdir(parents=True)
    tty = sys / 'class/tty/ttyACM4'
    tty.mkdir(parents=True)
    (tty / 'device').symlink_to(usb, target_is_directory=True)
    fields = {'idVendor': '05ac', 'idProduct': '4144', 'product': 'Orchard j71s NFS',
              'serial': f'PROFILE:j71s ROOT:{root} BOOT:{boot}'}
    for name, value in fields.items():
        (usb / name).write_text(value)
    assert find_nfs_serial(root, sys, dev) == dev / 'ttyACM4'
    for value in (f'PROFILE:j71s ROOT:{boot} BOOT:{boot}', f'PROFILE:j71s ROOT:{root} BOOT:bad'):
        (usb / 'serial').write_text(value)
        try:
            find_nfs_serial(root, sys, dev)
        except RuntimeError:
            pass
        else:
            raise AssertionError('mismatched identity accepted')
print('NFS serial selection accepts the staged root and rejects mismatches.')
