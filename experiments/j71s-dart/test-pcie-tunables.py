#!/usr/bin/env python3
"""Test the converter with synthetic data; no device tree required."""
import importlib.util
from pathlib import Path
import struct

p = Path(__file__).with_name('extract-pcie-tunables.py')
spec = importlib.util.spec_from_file_location('pcie_tunables', p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
record = lambda off, width, mask, value: struct.pack('<IIQQ', off, width, mask, value)
assert m.decode_table(record(4, 4, 0xff, 0x20), 16) == [(4, 0xff, 0x20)]
assert '<0x00000004 0x000000ff 0x00000020>' in m.render([('test', [(4, 0xff, 0x20)])])
assert m.tables_for_port(0)[2][0].endswith('pci-bridge0')
assert m.tables_for_port(1)[2][0].endswith('pci-bridge1')
assert m.tables_for_port(1)[2][2] == 'orchard,s8000-port1-tunables'
assert m.tables_for_port(1)[3][2] == 'orchard,s8000-root1-tunables'
try:
    m.tables_for_port(2)
except ValueError:
    pass
else:
    raise AssertionError('unsupported port accepted')
for raw, window in [
    (b'', 16), (b'\x00', 16), (record(4, 8, 1, 1), 16),
    (record(2, 4, 1, 1), 16), (record(16, 4, 1, 1), 16),
    (record(4, 4, 0x100000000, 0), 16), (record(4, 4, 1, 2), 16),
    (record(0, 4, 1, 1) * 257, 16),
]:
    try:
        m.decode_table(raw, window)
    except ValueError:
        pass
    else:
        raise AssertionError('invalid table accepted')
print('PCIe tunable conversion and malformed-input guards passed.')
