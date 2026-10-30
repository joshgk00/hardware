import importlib.util
from pathlib import Path
import struct
import unittest

spec = importlib.util.spec_from_file_location('pmu', Path(__file__).with_name('check-pmu-interrupt.py'))
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class Node:
    def __init__(self, properties):
        self.properties = properties


class Tree:
    def __init__(self, entries):
        self.entries = entries

    def walk(self):
        return iter(self.entries)


def fixture():
    handle = struct.pack('<I', 5)
    return [(check.PMU, Node({'interrupts': struct.pack('<II', 76, 0), 'interrupt-parent': handle})),
            (check.GPIO, Node({'AAPL,phandle': handle}))]


class ComparisonTests(unittest.TestCase):
    def test_matching_number_and_parent(self):
        self.assertTrue(all(check.compare(Tree(fixture())).values()))

    def test_bad_number_and_shape(self):
        for irq in (struct.pack('<II', 75, 76), struct.pack('<I', 76)):
            entries = fixture()
            entries[0][1].properties['interrupts'] = irq
            self.assertFalse(check.compare(Tree(entries))['interrupt-number'])

    def test_ambiguous_parent_and_duplicate_pmu(self):
        entries = fixture()
        entries.append(('/duplicate', Node({'phandle': struct.pack('<I', 5)})))
        self.assertFalse(check.compare(Tree(entries))['interrupt-parent'])
        entries.append(entries[0])
        self.assertFalse(any(check.compare(Tree(entries)).values()))


if __name__ == '__main__':
    unittest.main()
