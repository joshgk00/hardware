#!/usr/bin/env python3
"""Compare selected J71s ADT function references with upstream J71t candidates.

Only pass/fail results are printed. Raw ADTs can contain identities and
calibration; keep the input private. This does not access or enable hardware.
Requires orchard.apple.adt_tree from the unified Orchard checkout.
"""
import argparse
from collections import defaultdict
from pathlib import Path
import struct

WLAN = '/device-tree/arm-io/uart2/wlan'
UART = '/device-tree/arm-io/uart2'
PORT = '/device-tree/arm-io/apcie/pci-bridge1'
GPIO = '/device-tree/arm-io/gpio'
PMIC = '/device-tree/arm-io/i2c0/pmu'
CHECKS = (
    (WLAN, 'function-reg_on', PMIC, 14),
    (PORT, 'function-clkreq', GPIO, 165),
    (PORT, 'function-device_wake', GPIO, 67),
    (PORT, 'function-perst', GPIO, 161),
    (UART, 'function-tx', GPIO, 192),
    (UART, 'function-rts', GPIO, 194),
)


def compare(root):
    entries = list(root.walk())
    selected = {WLAN, UART, PORT, GPIO, PMIC}
    nodes = {}
    for path, node in entries:
        if path in selected:
            if path in nodes:
                raise ValueError('duplicate selected ADT path')
            nodes[path] = node
    refs = defaultdict(set)
    for path, node in entries:
        for name in ('AAPL,phandle', 'phandle'):
            raw = node.properties.get(name)
            if raw is not None:
                if len(raw) != 4:
                    raise ValueError('invalid ADT phandle length')
                refs[struct.unpack('<I', raw)[0]].add(path)
    result = {}
    for path, name, target, pin in CHECKS:
        raw = nodes.get(path).properties.get(name) if path in nodes else None
        if raw is None or len(raw) < 12 or len(raw) % 4:
            result[name] = False
            continue
        phandle = struct.unpack_from('<I', raw)[0]
        first_arg = struct.unpack_from('<I', raw, 8)[0]
        result[name] = refs.get(phandle) == {target} and first_arg == pin
    raw = nodes.get(WLAN).properties.get('interrupts') if WLAN in nodes else None
    result['wlan-interrupt-record'] = raw is not None and len(raw) == 8 and struct.unpack('<II', raw) == (113, 2)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('adt', type=Path, help='private local Apple device tree')
    args = parser.parse_args()
    from orchard.apple.adt_tree import parse
    try:
        checks = compare(parse(args.adt.read_bytes()))
    except (OSError, ValueError) as exc:
        parser.exit(1, f'Could not inspect ADT: {exc}\n')
    for name, matches in checks.items():
        print(f'{name}: {"matches" if matches else "missing or differs"}')
    if not all(checks.values()):
        parser.exit(1, 'One or more candidate references did not match.\n')
    print('Source comparison only; wiring, polarity and function remain unverified.')


if __name__ == '__main__':
    main()
