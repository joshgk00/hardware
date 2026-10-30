#!/usr/bin/env python3
"""Exercise the actual guard with synthetic J71s identity and mount evidence."""
import ast
from pathlib import Path
import subprocess
import tempfile

source = Path(__file__).with_name('prepare-nfs-test-root.py').read_text()
module = ast.parse(source)
assignment = next(n for n in module.body if isinstance(n, ast.Assign)
                  and any(isinstance(t, ast.Name) and t.id == 'CHECK_TEMPLATE' for t in n.targets))
template = ast.literal_eval(assignment.value)
with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    compatible = root / 'compatible'
    state = root / 'state'
    mountinfo = root / 'mountinfo'
    uname = root / 'uname'
    uname.write_text('#!/bin/sh\nprintf "%s\\n" 7.3.0-rc1\n')
    uname.chmod(0o755)
    script = (template.replace('@RELEASE@', '7.3.0-rc1')
              .replace('/proc/device-tree/compatible', str(compatible))
              .replace('/run/orchard/nfs-handoff-state', str(state))
              .replace('/proc/self/mountinfo', str(mountinfo)))
    guard = root / 'guard'
    guard.write_text(script)
    def run(expected):
        result = subprocess.run(['/bin/sh', str(guard)], env={'PATH': temp + ':/usr/bin:/bin'},
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        assert (result.returncode == 0) == expected
    compatible.write_bytes(b'apple,j71s\0apple,s8000\0')
    state.write_text('ready\n')
    mountinfo.write_text('42 1 0:42 / / rw - nfs4 server:/orchard-root rw\n')
    run(True)
    compatible.write_bytes(b'apple,j71b\0')
    run(False)
    compatible.write_bytes(b'apple,j71s\0')
    state.write_text('failed\n')
    run(False)
    state.write_text('ready\n')
    mountinfo.write_text('42 1 0:42 / / rw - ext4 /dev/example rw\n')
    run(False)
    mountinfo.write_text('42 1 0:42 / / rw - nfs4 server:/orchard-root rw\n')
    uname.write_text('#!/bin/sh\nprintf "%s\\n" wrong-kernel\n')
    run(False)
print('J71s NFS guard accepts matching state and rejects mismatches.')
