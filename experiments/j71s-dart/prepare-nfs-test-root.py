#!/usr/bin/env python3
"""Prepare a disposable Omarchy root for a guarded J71s NFS boot.

Run as UID 0 in the same user namespace that owns the extracted root. This
alters the supplied test root only; it never accesses an iPad or internal disk.
"""
import argparse
import json
import os
from pathlib import Path
import re

parser = argparse.ArgumentParser()
parser.add_argument('root', type=Path)
args = parser.parse_args()
root = args.root.resolve(strict=True)
if os.geteuid() != 0 or not root.is_dir():
    parser.error('run as root inside the root filesystem owner namespace')
receipt_path = root / 'etc/orchard/nfs-root.json'
receipt = json.loads(receipt_path.read_text())
release = receipt.get('kernel_release', '')
if (receipt.get('kind') != 'orchard.nfs-root' or receipt.get('profile') != 'j71s'
        or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._+-]{0,127}', release)):
    parser.error('expected a valid J71s NFS-root receipt')
dropin = root / 'etc/systemd/system/getty@tty1.service.d/20-j71b-platform.conf'
charge = root / 'etc/systemd/system/multi-user.target.wants/j71b-charge.service'
expected_dropin = '[Unit]\nRequires=j71b-platform-ready.service\nAfter=j71b-platform-ready.service\n'
if not dropin.is_file() or dropin.is_symlink() or dropin.read_text() != expected_dropin:
    parser.error('unexpected original J71b getty guard')
if not charge.is_symlink() or os.readlink(charge) != '/usr/lib/systemd/system/j71b-charge.service':
    parser.error('unexpected J71b charging service link')
checker = root / 'usr/local/libexec/j71s-nfs-check-platform'
unit = root / 'etc/systemd/system/j71s-nfs-platform-ready.service'
backup = dropin.with_suffix('.conf.disabled-j71s-nfs')
for path in (checker, unit, backup):
    if path.exists() or path.is_symlink():
        parser.error('refusing to overwrite: ' + str(path))
script = '''#!/bin/sh
# This guard applies only to the private J71s NFS-root experiment.
set -eu
[ "$(uname -r)" = '@RELEASE@' ]
tr '\\000' '\\n' < /proc/device-tree/compatible | grep -Fxq apple,j71s
[ "$(cat /run/orchard/nfs-handoff-state)" = ready ]
awk '$5 == "/" { for (i=6; i<=NF; i++) if ($i == "-" && $(i+1) ~ /^nfs4?$/) found=1 } END { exit !found }' /proc/self/mountinfo
'''.replace('@RELEASE@', release)
checker.write_text(script)
checker.chmod(0o755)
unit.write_text('[Unit]\nDescription=Verify J71s experimental NFS boot\n'
                'Before=getty@tty1.service\n\n[Service]\nType=oneshot\n'
                'ExecStart=/usr/local/libexec/j71s-nfs-check-platform\nRemainAfterExit=yes\n')
unit.chmod(0o644)
dropin.rename(backup)
dropin.write_text('[Unit]\nRequires=j71s-nfs-platform-ready.service\nAfter=j71s-nfs-platform-ready.service\n')
dropin.chmod(0o644)
charge.unlink()
print('Prepared J71s NFS test-root guard; J71b charging lease is disabled in this copy.')
