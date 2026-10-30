"""Locate the explicitly staged J71s NFS rescue console without exposing IDs."""
from pathlib import Path
import uuid
import re


def find_nfs_serial(root_id, location, sys_root=Path('/sys'), dev_root=Path('/dev')):
    if str(uuid.UUID(root_id)) != root_id:
        raise ValueError('Expected a canonical NFS root UUID')
    if not re.fullmatch(r'[0-9]+-[0-9]+(?:\.[0-9]+)*', location):
        raise ValueError('Expected a Linux USB physical location')
    candidates = []
    for tty in (sys_root / 'class/tty').glob('ttyACM*'):
        try:
            parent = (tty / 'device').resolve(strict=True)
            usb = next(p for p in (parent, *parent.parents)
                       if (p / 'idVendor').is_file() and (p / 'idProduct').is_file())
            if (usb.name != location or (usb / 'idVendor').read_text().strip().lower() != '05ac' or
                    (usb / 'idProduct').read_text().strip().lower() != '4144' or
                    (usb / 'product').read_text().strip() != 'Orchard j71s NFS'):
                continue
            fields = (usb / 'serial').read_text().strip().split()
            if len(fields) != 3 or fields[:2] != ['PROFILE:j71s', 'ROOT:' + root_id] or not fields[2].startswith('BOOT:'):
                continue
            boot = fields[2][5:]
            if str(uuid.UUID(boot)) != boot:
                continue
            candidates.append(dev_root / tty.name)
        except (OSError, StopIteration, ValueError):
            continue
    if len(candidates) != 1:
        raise RuntimeError(f'Expected one matching J71s NFS serial console, found {len(candidates)}')
    return candidates[0]


def find_nfs_interface(root_id, location, sys_root=Path('/sys'), dev_root=Path('/dev')):
    """Find the sole network interface belonging to the selected NFS console."""
    serial = find_nfs_serial(root_id, location, sys_root, dev_root)
    serial_device = (sys_root / 'class/tty' / serial.name / 'device').resolve(strict=True)
    usb = next(p for p in (serial_device, *serial_device.parents)
               if (p / 'idVendor').is_file() and (p / 'idProduct').is_file())
    candidates = []
    for net in (sys_root / 'class/net').iterdir():
        try:
            parent = (net / 'device').resolve(strict=True)
            if usb in (parent, *parent.parents):
                candidates.append(net.name)
        except OSError:
            continue
    if len(candidates) != 1:
        raise RuntimeError(f'Expected one matching J71s NFS interface, found {len(candidates)}')
    return candidates[0]
