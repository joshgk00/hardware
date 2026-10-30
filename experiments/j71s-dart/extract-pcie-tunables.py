#!/usr/bin/env python3
"""Convert J71s Apple DT PCIe tunables into a private DTS property fragment.

Requires the unified orchard.apple.adt_tree parser, or the older
orchard_cli.apple.adt_tree parser. Output contains device-derived configuration;
review its destination and do not commit it to a public repo. The result is data
only and does not enable PCIe or perform hardware writes.
"""
import argparse
import os
from pathlib import Path
import struct

RECORD = struct.Struct('<IIQQ')


def tables_for_port(port):
    if port not in (0, 1):
        raise ValueError('unsupported PCIe port')
    bridge = f'/device-tree/arm-io/apcie/pci-bridge{port}'
    return (
        ('/device-tree/arm-io/apcie', 'apcie-common-tunables', 'orchard,s8000-common-tunables', 0x8000),
        ('/device-tree/arm-io/apcie', 'apcie-phy-tunables', 'orchard,s8000-phy-tunables', 0x4000),
        (bridge, 'apcie-config-tunables', f'orchard,s8000-port{port}-tunables', 0x4000),
        (bridge, 'pcie-rc-tunables', f'orchard,s8000-root{port}-tunables', 0x1000),
    )


def decode_table(raw, window):
    if not raw or len(raw) % RECORD.size:
        raise ValueError('missing or truncated tunable table')
    if len(raw) // RECORD.size > 256:
        raise ValueError('too many tunable records')
    result = []
    for offset, width, mask, value in RECORD.iter_unpack(raw):
        if width != 4 or offset % 4 or offset + 4 > window:
            raise ValueError('unsupported width, alignment, or offset')
        if mask > 0xffffffff or value > 0xffffffff or value & ~mask:
            raise ValueError('invalid mask or value')
        result.append((offset, mask, value))
    return result


def render(tables):
    lines = ['/* Private device-derived data; do not publish. */']
    for name, records in tables:
        lines.append(f'{name} =')
        for i, (offset, mask, value) in enumerate(records):
            end = ';' if i == len(records) - 1 else ','
            lines.append(f'    <0x{offset:08x} 0x{mask:08x} 0x{value:08x}>{end}')
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('adt', type=Path, help='local Apple device tree file')
    parser.add_argument('output', type=Path, help='new private DTS fragment')
    parser.add_argument('--port', type=int, choices=(0, 1), default=0,
                        help='candidate PCIe port to extract (default: 0)')
    args = parser.parse_args()
    try:
        from orchard.apple.adt_tree import parse
    except ModuleNotFoundError as exc:
        if exc.name not in ('orchard', 'orchard.apple', 'orchard.apple.adt_tree'):
            raise
        from orchard_cli.apple.adt_tree import parse
    nodes = dict(parse(args.adt.read_bytes()).walk())
    tables = []
    for path, prop, name, window in tables_for_port(args.port):
        try:
            raw = nodes[path].properties[prop]
        except KeyError as exc:
            raise SystemExit(f'Missing required node or property: {path} {prop}') from exc
        tables.append((name, decode_table(raw, window)))
    # Refuse to overwrite files or follow an existing symlink.
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as output:
            output.write(render(tables))
    except BaseException:
        args.output.unlink(missing_ok=True)
        raise
    print(f'Wrote {len(tables)} validated tables to private file {args.output}')


if __name__ == '__main__':
    main()
