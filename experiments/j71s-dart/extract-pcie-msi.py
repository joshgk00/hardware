#!/usr/bin/env python3
"""Extract candidate PCIe MSI properties from an Apple DT to a private file.

The output is an unverified candidate for a Linux PCIe host, not an enabled
interrupt controller. Keep device-derived values private until reviewed.
"""
import argparse
import os
from pathlib import Path
import struct

ROOT = '/device-tree/arm-io/apcie'
AIC = '/device-tree/arm-io/aic'


def scalar(props, name, size):
    data = props.get(name)
    if data is None or len(data) != size:
        raise ValueError(f'missing or malformed {name}')
    return int.from_bytes(data, 'little')


def decode(nodes):
    try:
        root = nodes[ROOT].properties
        aic = nodes[AIC].properties
    except KeyError as exc:
        raise ValueError('missing PCIe or AIC node') from exc
    parent = scalar(root, 'msi-parent-controller', 4)
    if not parent or parent != scalar(aic, 'AAPL,phandle', 4):
        raise ValueError('MSI parent is not the expected AIC')
    base = scalar(root, 'msi-vector-offset', 4)
    count = scalar(root, '#msi-vectors', 4)
    address = scalar(root, 'msi-address', 8)
    if not count or count > 256 or base + count > 0x100000000:
        raise ValueError('invalid root vector range')
    # The current H9P binding and driver consume one 32-bit DT cell.
    if not address or address & 0xfff or address > 0xffffffff:
        raise ValueError('invalid MSI address')
    ranges = []
    for port in range(4):
        path = f'{ROOT}/pci-bridge{port}'
        if path not in nodes:
            continue
        props = nodes[path].properties
        start = scalar(props, 'msi-vector-base', 4)
        nvec = scalar(props, '#msi-vectors', 4)
        if not nvec or start + nvec > count:
            raise ValueError('port vector range outside root range')
        if any(start < old_start + old_count and old_start < start + nvec
               for old_start, old_count in ranges):
            raise ValueError('overlapping port vector ranges')
        ranges.append((start, nvec))
    if not ranges:
        raise ValueError('no PCIe port vectors')
    return base, count, address, ranges


def render(data):
    base, count, address, ranges = data
    lines = ['/* Candidate device-derived data; keep private and validate. */',
             f'msi-ranges = <&aic AIC_IRQ {base} IRQ_TYPE_EDGE_RISING {count}>;',
             f'apple,msi-doorbell = <0x{address:x}>;',
             '/* Port ranges are offsets into the root vector range: */']
    lines.extend(f'/* port range {start} + {count} */' for start, count in ranges)
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('adt', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        from orchard.apple.adt_tree import parse
    except ModuleNotFoundError as exc:
        if exc.name not in ('orchard', 'orchard.apple', 'orchard.apple.adt_tree'):
            raise
        from orchard_cli.apple.adt_tree import parse
    try:
        result = decode(dict(parse(args.adt.read_bytes()).walk()))
    except ValueError as exc:
        parser.error(str(exc))
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            out.write(render(result))
    except BaseException:
        args.output.unlink(missing_ok=True)
        raise
    print('Wrote candidate MSI data to private file', args.output)


if __name__ == '__main__':
    main()
