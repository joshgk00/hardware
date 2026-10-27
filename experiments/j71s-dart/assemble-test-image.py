#!/usr/bin/env python3
"""Assemble the exact researched DART0 RAM image from local test artifacts.

This creates a file only. It does not connect to or boot a device.
"""
import argparse
import hashlib
import json
from pathlib import Path

NAMES = ('loader', 'bootargs', 'dtb', 'kernel', 'initramfs_header', 'initramfs')
BASE_SHA = 'b5c71d53c91a8ae931ebde589829587dc3e22fe6917c919c2fbfe8117ab9a3d5'
DART_DTB_SHA = 'a7e48f28fc49912e8a6f52db95314e71cd241a546d1191bfeab1aed7a1c4cec1'
DART_KERNEL_SHA = 'ae14ae272de5690015aa63f16e49543eca9f48bface744c8c860d88052f22d84'
IMAGE_SHA = '9187433e84fd6385bc92a9ed9e3738e221ca55ee2bbe92c1b58acf92383d711f'
MARKER_KERNEL_SHA = 'b6dabc64d164eb269ea3298e97f85ff765a97174d496f82069c9a61e1e07d17e'
MARKER_IMAGE_SHA = 'f1257433e1ee7f51b91763bdd3796d2c0ee138469a142496d69d96e6114a73d6'
CONSUMER_DTB_SHA = '0e106b8b57c3b885ef812e2f4f6ebd77f479727c6825110b8bdee87950eaf063'
CONSUMER_KERNEL_SHA = '234b47c3809ae27b45d3f74399392f0f764105c58ba864269736ba5061044dff'
CONSUMER_IMAGE_SHA = '5c62e11b55188742cd80f4c7edf9d6f20a6076d44dec52c811af86e40e6673e2'


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def split_components(data: bytes, manifest: dict) -> dict:
    if digest(data) != manifest.get('image_sha256'):
        raise ValueError('baseline image digest mismatch')
    entries = manifest.get('components')
    if (not isinstance(entries, list) or not all(isinstance(x, dict) for x in entries)
            or tuple(x.get('name') for x in entries) != NAMES):
        raise ValueError('unexpected component sequence')
    offset = 0
    components = {}
    for entry in entries:
        size = entry.get('bytes')
        if type(size) is not int or size <= 0 or entry.get('offset') != offset:
            raise ValueError('invalid component range')
        chunk = data[offset:offset + size]
        if len(chunk) != size or digest(chunk) != entry.get('sha256'):
            raise ValueError('component digest or size mismatch')
        components[entry['name']] = chunk
        offset += size
    if offset != len(data):
        raise ValueError('unaccounted image bytes')
    return components


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('dart_dtb', type=Path)
    parser.add_argument('dart_kernel', type=Path)
    parser.add_argument('output', type=Path)
    variants = parser.add_mutually_exclusive_group()
    variants.add_argument('--reset-markers', action='store_true', help='assemble the separately built reset-marker diagnostic')
    variants.add_argument('--software-consumer', action='store_true', help='assemble the software-only consumer diagnostic')
    args = parser.parse_args()
    try:
        data = args.baseline.read_bytes()
        if digest(data) != BASE_SHA:
            raise ValueError('unexpected baseline image')
        components = split_components(data, json.loads(args.manifest.read_text()))
        components['dtb'] = args.dart_dtb.read_bytes()
        components['kernel'] = args.dart_kernel.read_bytes()
        kernel_sha = CONSUMER_KERNEL_SHA if args.software_consumer else (MARKER_KERNEL_SHA if args.reset_markers else DART_KERNEL_SHA)
        image_sha = CONSUMER_IMAGE_SHA if args.software_consumer else (MARKER_IMAGE_SHA if args.reset_markers else IMAGE_SHA)
        dtb_sha = CONSUMER_DTB_SHA if args.software_consumer else DART_DTB_SHA
        if digest(components['dtb']) != dtb_sha or digest(components['kernel']) != kernel_sha:
            raise ValueError('unexpected DART tree or kernel')
        image = b''.join(components[name] for name in NAMES)
        if digest(image) != image_sha:
            raise ValueError('unexpected assembled image')
        with args.output.open('xb') as stream:
            stream.write(image)
        print('Verified DART0 test image:', args.output)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f'Image assembly failed: {exc}\n')


if __name__ == '__main__':
    main()
