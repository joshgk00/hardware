import importlib.util
from pathlib import Path
import struct
import unittest

spec = importlib.util.spec_from_file_location('wlan_check', Path(__file__).with_name('check-wlan-signals.py'))
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class Node:
    def __init__(self, properties=None):
        self.properties = properties or {}


class Tree:
    def __init__(self, entries):
        self.entries = entries

    def walk(self):
        return iter(self.entries)


def fixture():
    nodes = {p: Node() for p in (check.WLAN, check.UART, check.PORT, check.GPIO, check.PMIC)}
    nodes[check.GPIO].properties['AAPL,phandle'] = struct.pack('<I', 1)
    nodes[check.PMIC].properties['AAPL,phandle'] = struct.pack('<I', 2)
    for path, name, target, pin in check.CHECKS:
        handle = 1 if target == check.GPIO else 2
        nodes[path].properties[name] = struct.pack('<I4sII', handle, b'test', pin, 0)
    nodes[check.WLAN].properties['interrupts'] = struct.pack('<II', 113, 2)
    return nodes


class SignalComparisonTests(unittest.TestCase):
    def test_expected_records_match(self):
        self.assertTrue(all(check.compare(Tree(list(fixture().items()))).values()))

    def test_pin_in_wrong_word_does_not_match(self):
        nodes = fixture()
        nodes[check.PORT].properties['function-perst'] = struct.pack('<I4sII', 1, b'test', 0, 161)
        self.assertFalse(check.compare(Tree(list(nodes.items())))['function-perst'])

    def test_ambiguous_reference_and_missing_interrupt_fail(self):
        nodes = fixture()
        nodes['/duplicate-handle'] = Node({'phandle': struct.pack('<I', 1)})
        del nodes[check.WLAN].properties['interrupts']
        result = check.compare(Tree(list(nodes.items())))
        self.assertFalse(result['function-perst'])
        self.assertFalse(result['wlan-interrupt-record'])

    def test_interrupt_flags_must_match(self):
        nodes = fixture()
        nodes[check.WLAN].properties['interrupts'] = struct.pack('<II', 113, 3)
        self.assertFalse(check.compare(Tree(list(nodes.items())))['wlan-interrupt-record'])

    def test_duplicate_path_is_rejected(self):
        nodes = fixture()
        with self.assertRaises(ValueError):
            check.compare(Tree([*nodes.items(), (check.GPIO, Node())]))


if __name__ == '__main__':
    unittest.main()
