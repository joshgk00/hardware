#!/usr/bin/env python3
"""Compare private J71s PMU and Tristar ADT records with J71t candidates.

This checks only the number and parent, not flags, polarity or hardware behavior.
Raw ADTs contain private device data; this tool prints only pass/fail results.
"""
import argparse
from pathlib import Path
import struct

PMU = '/device-tree/arm-io/i2c0/pmu'
GPIO = '/device-tree/arm-io/gpio'
TRISTAR = '/device-tree/arm-io/i2c0/tristar'


def compare(root):
    entries = list(root.walk())
    nodes = {path: [node for candidate, node in entries if candidate == path]
             for path in (PMU, TRISTAR)}
    props = nodes[PMU][0].properties if len(nodes[PMU]) == 1 else {}
    irq = props.get('interrupts', b'')
    parent = props.get('interrupt-parent', b'')
    refs = {path for path, node in entries
            if len(parent) == 4 and any(node.properties.get(key) == parent
                                        for key in ('AAPL,phandle', 'phandle'))}
    result = {'interrupt-number': len(irq) == 8 and struct.unpack_from('<I', irq)[0] == 76,
              'interrupt-parent': refs == {GPIO}}
    for label, path, address in (('pmu-address', PMU, 0x3c), ('tristar-address', TRISTAR, 0x1a)):
        reg = nodes[path][0].properties.get('reg', b'') if len(nodes[path]) == 1 else b''
        result[label] = len(reg) == 16 and struct.unpack_from('<I', reg)[0] == address
    return result


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
    print('Selected raw fields only; flags, chip revisions and hardware behavior remain unverified.')


if __name__ == '__main__':
    main()
