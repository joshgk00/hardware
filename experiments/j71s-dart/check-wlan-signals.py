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
WIFI_ENDPOINT = PORT + '/wlan'
STORAGE_PORT = '/device-tree/arm-io/apcie/pci-bridge0'
GPIO = '/device-tree/arm-io/gpio'
PMIC = '/device-tree/arm-io/i2c0/pmu'
DART0 = '/device-tree/arm-io/dart-apcie0'
DART1 = '/device-tree/arm-io/dart-apcie1'
MAPPER1 = DART1 + '/mapper-apcie1'
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
    selected = {WLAN, UART, PORT, WIFI_ENDPOINT, STORAGE_PORT, GPIO, PMIC, DART0, DART1, MAPPER1}
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
    for name, path, target in (('port0-dart-reference', STORAGE_PORT, DART0),
                               ('port1-dart-reference', PORT, DART1)):
        raw = nodes.get(path).properties.get('function-dart_force_active') if path in nodes else None
        result[name] = (raw is not None and len(raw) == 8 and
                        refs.get(struct.unpack_from('<I', raw)[0]) == {target})
    parent = nodes.get(WIFI_ENDPOINT).properties.get('iommu-parent') if WIFI_ENDPOINT in nodes else None
    result['wlan-mapper-reference'] = (parent is not None and len(parent) == 4 and
                                       refs.get(struct.unpack('<I', parent)[0]) == {MAPPER1})
    for name, path, expected_size in (('port0-window-candidate', DART0, 0x3c000000),
                                       ('port1-window-candidate', DART1, 0x3ffff000)):
        props = nodes[path].properties if path in nodes else {}
        offset, size = props.get('vm-offset'), props.get('vm-size')
        result[name] = (offset is not None and len(offset) == 8 and
                        size is not None and len(size) == 4 and
                        struct.unpack_from('<I', offset)[0] == 0x80000000 and
                        struct.unpack('<I', size)[0] == expected_size)
    for index, path, address in ((0, DART0, 0x601008000), (1, DART1, 0x602008000)):
        props = nodes[path].properties if path in nodes else {}
        reg = props.get('reg')
        result[f'port{index}-dart-register-candidate'] = (
            reg is not None and len(reg) == 16 and struct.unpack('<QQ', reg) == (address, 0x4000))
        reflector, fetch, diag = (props.get('error-reflector'), props.get('fetch-config'),
                                  props.get('diag-config'))
        result[f'port{index}-dart-init-candidate'] = (
            reflector is not None and len(reflector) == 16 and
            struct.unpack_from('<Q', reflector)[0] == 0x20fffc000 and
            fetch is not None and len(fetch) == 4 and struct.unpack('<I', fetch)[0] == 0xe0303 and
            diag is not None and len(diag) == 4 and struct.unpack('<I', diag)[0] == 0x100)
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
    print('Source comparison only; wiring, DMA isolation and function remain unverified.')


if __name__ == '__main__':
    main()
