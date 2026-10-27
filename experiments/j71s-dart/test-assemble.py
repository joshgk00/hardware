#!/usr/bin/env python3
"""Exercise the image component validation with synthetic data."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('dart_assembly', Path(__file__).with_name('assemble-test-image.py'))
assembly = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assembly)


def fixture():
    chunks = [name.encode() for name in assembly.NAMES]
    data = b''.join(chunks)
    entries = []
    pos = 0
    for name, chunk in zip(assembly.NAMES, chunks):
        entries.append({'name': name, 'offset': pos, 'bytes': len(chunk), 'sha256': assembly.digest(chunk)})
        pos += len(chunk)
    return data, {'image_sha256': assembly.digest(data), 'components': entries}


class AssemblyTests(unittest.TestCase):
    def test_reconstructs_all_components(self):
        data, manifest = fixture()
        result = assembly.split_components(data, manifest)
        self.assertEqual(b''.join(result[n] for n in assembly.NAMES), data)

    def test_rejects_mutated_input_and_invalid_ranges(self):
        data, manifest = fixture()
        with self.assertRaises(ValueError):
            assembly.split_components(data + b'X', manifest)
        manifest['components'][1]['offset'] += 1
        with self.assertRaises(ValueError):
            assembly.split_components(data, manifest)

    def test_rejects_wrong_component_order_and_digest(self):
        data, manifest = fixture()
        manifest['components'][0]['sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            assembly.split_components(data, manifest)
        data, manifest = fixture()
        manifest['components'].reverse()
        with self.assertRaises(ValueError):
            assembly.split_components(data, manifest)


if __name__ == '__main__':
    unittest.main()
