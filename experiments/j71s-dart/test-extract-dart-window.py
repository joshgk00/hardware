#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import struct
spec=importlib.util.spec_from_file_location('window',Path(__file__).with_name('extract-dart-window.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class N:
 def __init__(self,p):self.properties=p
pack=lambda *v:struct.pack('<'+'I'*len(v),*v)
def sample():
 return {m.DART:N({'vm-offset':pack(0x80000000,0x40000000),'vm-size':pack(0x3c000000)}),
         m.MAPPER:N({'AAPL,phandle':pack(7),'reg':pack(0)}),
         m.ENDPOINT:N({'iommu-parent':pack(7,2,3)})}
assert m.decode(sample())==(0x80000000,0x3c000000)
def reject(fn):
 n=sample();fn(n)
 try:m.decode(n)
 except ValueError:return
 raise AssertionError('invalid device tree accepted')
reject(lambda n:n[m.DART].properties.update({'vm-offset':b'x'}))
reject(lambda n:n[m.DART].properties.update({'vm-size':pack(0)}))
reject(lambda n:n[m.ENDPOINT].properties.update({'iommu-parent':pack(9,2,3)}))
reject(lambda n:n[m.MAPPER].properties.update({'reg':pack(1)}))
reject(lambda n:n[m.DART].properties.update({'vm-offset':pack(0x80000000,0x80000000)}))
print('Candidate DART window extraction and failure guards passed.')
