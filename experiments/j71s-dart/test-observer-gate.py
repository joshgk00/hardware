#!/usr/bin/env python3
"""Check the observer gate using only temporary files and fake BusyBox."""
import os
from pathlib import Path
import subprocess
import tempfile

source = (Path(__file__).parent / "observe-and-start-j71s-identify.sh").read_text()
device = "/dev/kmsg"
gate_path = "/sys/module/pcie_j71s_diagnostic/parameters/identify_start"
assert source.count(device) == 2  # availability check and open
assert source.count(gate_path) == 1

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    (root / "kmsg").write_text("")
    gate = root / "gate"
    gate.write_text("")
    script = root / "observer.sh"
    script.write_text(source.replace(device, str(root / "kmsg"))
                      .replace(gate_path, str(gate)))
    busybox = root / "busybox"
    env = dict(os.environ, PATH=str(root) + os.pathsep + os.environ["PATH"])

    def run(fake):
        busybox.write_text(fake)
        busybox.chmod(0o755)
        return subprocess.run(["sh", str(script)], env=env, text=True,
                              capture_output=True, check=True, timeout=10).stdout

    output = run("#!/bin/sh\nexit 1\n")
    assert "observer exited; no command requested" in output
    assert gate.read_text() == ""
    output = run("#!/bin/sh\nsleep 2\nexit 0\n")
    assert "start gate enabled" in output
    assert gate.read_text() == "1\n"

print("Observer gate checks passed using temporary files.")
