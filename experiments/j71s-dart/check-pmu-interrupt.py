#!/usr/bin/env python3
"""Compare a private J71s ADT's PMU interrupt with the J71t candidate.

This checks only the number and parent, not flags, polarity or hardware behavior.
Raw ADTs contain private device data; this tool prints only pass/fail results.
"""
import argparse
from pathlib import Path
import struct

PMU = '/device-tree/arm-io/i2c0/pmu'
GPIO = '/device-tree/arm-io/gpio'


def compare(root):
    entries = list(root.walk())
    pmus = [node for path, node in entries if path == PMU]
    if len(pmus) != 1:
        return {'interrupt-number': False, 'interrupt-parent': False}
    props = pmus[0].properties
    irq = props.get('interrupts', b'')
    parent = props.get('interrupt-parent', b'')
    refs = {path for path, node in entries
            if len(parent) == 4 and any(node.properties.get(key) == parent
                                        for key in ('AAPL,phandle', 'phandle'))}
    return {'interrupt-number': len(irq) == 8 and struct.unpack_from('<I', irq)[0] == 76,
            'interrupt-parent': refs == {GPIO}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('adt', type=Path)
    args = parser.parse_args()
    from orchard.apple.adt_tree import parse
    try:
        result = compare(parse(args.adt.read_bytes()))
    except (OSError, ValueError) as exc:
        parser.exit(1, f'Could not inspect ADT: {exc}\n')
    for name, matches in result.items():
        print(f'{name}: {"matches" if matches else "missing or differs"}')
    if not all(result.values()):
        parser.exit(1, 'Candidate did not match.\n')
    print('Number and parent only; flags and hardware behavior remain unverified.')


if __name__ == '__main__':
    main()
