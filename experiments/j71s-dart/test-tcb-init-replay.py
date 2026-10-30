#!/usr/bin/env python3
"""Replay the TCB init header's dependent patches, including the pre-init guard."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parent
patches = ('j71s-identify-descriptor-probe.patch',
           'j71s-diagnostic-armed-host-hold.patch', 'j71s-tcb-fifo-once.patch')
with tempfile.TemporaryDirectory() as temp:
    directory = Path(temp) / 'drivers/pci/controller'
    directory.mkdir(parents=True)
    target = directory / 'j71s-tcb-init-test.h'
    target.write_text((root / 'driver-patch/j71s-tcb-init-test.h').read_text())
    for name in patches:
        # These multi-file patches also touch the coordinator; replay only this header.
        header_patch = (root / name).read_text().split('\n--- a/')[0] + '\n'
        subprocess.run(['patch', '-p1', '--batch'], cwd=temp, input=header_patch,
                       text=True, check=True, capture_output=True)
    result = target.read_text()
    markers = ('TCB pre-init FIFO:', 'writel(0x10000, mmu + 0x04)',
               'TCB init experiment: armed=1', 'TCB FIFO experiment:')
    positions = [result.index(marker) for marker in markers]
    if positions != sorted(positions) or 'WRITE_ONCE(j71s_once_tcb_armed, true)' not in result:
        raise SystemExit('Invalid TCB initialization sequence or retention guard')
print('TCB init dependent patches replay and preserve guard ordering.')
