#!/usr/bin/env python3
"""Exercise NFS serial selection with synthetic sysfs identities."""
from pathlib import Path
from tempfile import TemporaryDirectory
from j71s_nfs_serial import find_nfs_serial, find_nfs_interface

root = '00000000-0000-4000-8000-000000000001'
boot = '00000000-0000-4000-8000-000000000002'
with TemporaryDirectory() as temporary:
    sys = Path(temporary) / 'sys'
    dev = Path(temporary) / 'dev'
    usb = sys / 'devices/usb/1-2.3'
    usb.mkdir(parents=True)
    tty = sys / 'class/tty/ttyACM4'
    tty.mkdir(parents=True)
    (tty / 'device').symlink_to(usb, target_is_directory=True)
    fields = {'idVendor': '05ac', 'idProduct': '4144', 'product': 'Orchard j71s NFS',
              'serial': f'PROFILE:j71s ROOT:{root} BOOT:{boot}'}
    for name, value in fields.items():
        (usb / name).write_text(value)
    assert find_nfs_serial(root, '1-2.3', sys, dev) == dev / 'ttyACM4'
    try:
        find_nfs_serial(root, '1-9', sys, dev)
    except RuntimeError:
        pass
    else:
        raise AssertionError('wrong physical port accepted')
    net = sys / 'class/net/usbtest'
    net.mkdir(parents=True)
    network_device = usb / 'network'
    network_device.mkdir()
    (net / 'device').symlink_to(network_device, target_is_directory=True)
    assert find_nfs_interface(root, '1-2.3', sys, dev) == 'usbtest'
    extra = sys / 'class/net/other'
    extra.mkdir()
    (extra / 'device').symlink_to(network_device, target_is_directory=True)
    try:
        find_nfs_interface(root, '1-2.3', sys, dev)
    except RuntimeError:
        pass
    else:
        raise AssertionError('ambiguous interfaces accepted')
    (extra / 'device').unlink()
    extra.rmdir()
    for value in (f'PROFILE:j71s ROOT:{boot} BOOT:{boot}', f'PROFILE:j71s ROOT:{root} BOOT:bad'):
        (usb / 'serial').write_text(value)
        try:
            find_nfs_serial(root, '1-2.3', sys, dev)
        except RuntimeError:
            pass
        else:
            raise AssertionError('mismatched identity accepted')
print('NFS serial selection accepts the staged root and rejects mismatches.')
