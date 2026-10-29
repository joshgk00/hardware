#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import struct

spec = importlib.util.spec_from_file_location('msi', Path(__file__).with_name('extract-pcie-msi.py'))
msi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(msi)
class Node:
    def __init__(self, **props):
        self.properties = props
u32 = lambda v: struct.pack('<I', v)
u64 = lambda v: struct.pack('<Q', v)
def sample():
    return {
        msi.ROOT: Node(**{'msi-parent-controller': u32(7), 'msi-vector-offset': u32(80),
                          '#msi-vectors': u32(32), 'msi-address': u64(0xbffff000)}),
        msi.AIC: Node(**{'AAPL,phandle': u32(7)}),
        msi.ROOT + '/pci-bridge0': Node(**{'msi-vector-base': u32(0), '#msi-vectors': u32(8)}),
        msi.ROOT + '/pci-bridge1': Node(**{'msi-vector-base': u32(8), '#msi-vectors': u32(8)}),
    }
assert msi.decode(sample()) == (80, 32, 0xbffff000, [(0, 8), (8, 8)])
assert 'AIC_IRQ 80 IRQ_TYPE_EDGE_RISING 32' in msi.render(msi.decode(sample()))
def reject(mutator):
    data=sample(); mutator(data)
    try: msi.decode(data)
    except ValueError: return
    raise AssertionError('invalid MSI metadata was accepted')
reject(lambda d: d[msi.ROOT].properties.update({'msi-parent-controller':u32(9)}))
reject(lambda d: d[msi.ROOT].properties.update({'msi-address':u64(3)}))
reject(lambda d: d[msi.ROOT].properties.update({'#msi-vectors':b'bad'}))
reject(lambda d: d[msi.ROOT+'/pci-bridge1'].properties.update({'msi-vector-base':u32(7)}))
reject(lambda d: d[msi.ROOT+'/pci-bridge1'].properties.update({'msi-vector-base':u32(30)}))
print('MSI extraction: valid, malformed, parent, range and overlap checks passed.')
