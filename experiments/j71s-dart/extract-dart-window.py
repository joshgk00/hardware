#!/usr/bin/env python3
"""Extract a provisional PCIe DART0 window from a private Apple DT.

The stream-to-offset relationship is not established by this tool. The emitted
experimental apple,dma-range property is not the current upstream H9P mapping
interface, which uses iommu-map. Do not use this output for physical DMA or as
an upstream device-tree fragment without independently validating the mapping.
"""
import argparse
import os
from pathlib import Path
import struct

DART = '/device-tree/arm-io/dart-apcie0'
MAPPER = DART + '/mapper-apcie0'
ENDPOINT = '/device-tree/arm-io/apcie/pci-bridge0/s3e'


def decode(nodes):
    try:
        dart = nodes[DART].properties
        mapper = nodes[MAPPER].properties
        endpoint = nodes[ENDPOINT].properties
        offsets = dart['vm-offset']
        size = dart['vm-size']
        handle = mapper['AAPL,phandle']
        parent = endpoint['iommu-parent']
        reg = mapper['reg']
    except KeyError as exc:
        raise ValueError('missing candidate DART, mapper or endpoint property') from exc
    if len(offsets) != 8 or len(size) != 4 or len(handle) != 4 or len(parent) != 12 or len(reg) != 4:
        raise ValueError('malformed DART or mapper property')
    first, second = struct.unpack('<II', offsets)
    length, = struct.unpack('<I', size)
    if not struct.unpack('<I', handle)[0] or parent[:4] != handle or struct.unpack('<I', reg)[0] != 0:
        raise ValueError('endpoint does not reference expected mapper zero')
    if first != 0x80000000 or length != 0x3c000000:
        raise ValueError('window differs from the tested provisional hypothesis')
    if second & 0xfff or first == second or second + length > 1 << 32:
        raise ValueError('invalid secondary offset')
    return first, length


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('adt', type=Path)
    ap.add_argument('output', type=Path)
    args = ap.parse_args()
    try:
        from orchard.apple.adt_tree import parse
    except ModuleNotFoundError as exc:
        if exc.name not in ('orchard', 'orchard.apple', 'orchard.apple.adt_tree'):
            raise
        from orchard_cli.apple.adt_tree import parse
    try:
        start, length = decode(dict(parse(args.adt.read_bytes()).walk()))
    except ValueError as exc:
        ap.error(str(exc))
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            out.write('/* Experimental legacy property, not upstream iommu-map; do not use for hardware DMA. */\n')
            out.write(f'apple,dma-range = /bits/ 64 <0x{start:x} 0x{length:x}>;\n')
    except BaseException:
        args.output.unlink(missing_ok=True)
        raise
    print('Wrote private candidate DART window to', args.output)


if __name__ == '__main__':
    main()
