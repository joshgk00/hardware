#!/usr/bin/env python3
"""Summarize bounded 64-bit little-endian Linux evdev records from J71s.

Input is the base64 section emitted by j71s-touch-capture.sh, not its full log.
The report includes event counts and coordinate ranges, not raw event records.
"""
import argparse
import base64
import json
from pathlib import Path
import struct

EVENT = struct.Struct('<qqHHi')
MAX_RECORDS = 512


def report(encoded):
    data = base64.b64decode(b''.join(encoded.split()), validate=True)
    if len(data) % EVENT.size or len(data) > EVENT.size * MAX_RECORDS:
        raise ValueError('Invalid bounded ARM64 input-event capture')
    counts = {'events': 0, 'frames': 0, 'dropped_frames': 0, 'touch_starts': 0, 'touch_ends': 0}
    x, y = [], []
    for _, _, typ, code, value in EVENT.iter_unpack(data):
        counts['events'] += 1
        if typ == 0 and code == 0:
            counts['frames'] += 1
        elif typ == 0 and code == 3:
            counts['dropped_frames'] += 1
        elif typ == 3 and code == 0x39:
            counts['touch_ends' if value == -1 else 'touch_starts'] += 1
        elif typ == 3 and code == 0x35:
            x.append(value)
        elif typ == 3 and code == 0x36:
            y.append(value)
    counts['x_range'] = [min(x), max(x)] if x else None
    counts['y_range'] = [min(y), max(y)] if y else None
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base64_file', type=Path)
    args = parser.parse_args()
    if args.base64_file.stat().st_size > 32768:
        parser.error('capture exceeds size limit')
    print(json.dumps(report(args.base64_file.read_bytes()), indent=2))


if __name__ == '__main__':
    main()
