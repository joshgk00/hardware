#!/usr/bin/env python3
"""Compile and exercise the actual shared HMB lookup with simulated OF data."""
from pathlib import Path
import subprocess
import tempfile

header = Path(__file__).parent / 'driver-patch/include/linux/apple-ans-hmb.h'
s = header.read_text()
patch = (header.parents[3] / 'dynamic-hmb-driver.patch').read_text()
assert ''.join(line[1:] for line in patch.splitlines(keepends=True)[patch.splitlines().index('+++ b/include/linux/apple-ans-hmb.h') + 2:] if line.startswith('+')) == s, 'test header differs from patch'
body = s[s.index('static inline int apple_ans_hmb_resource'):s.rindex('#endif')]
prefix = r'''
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#define RESOURCE_SIZE_MAX UINT64_MAX
#define IORESOURCE_MEM 0x200
struct resource { uint64_t start, end, flags; };
struct reserved_mem { uint64_t base, size; };
struct device_node { int reg, nomap, reusable, found, static_ret; struct reserved_mem r; };
static void *of_find_property(struct device_node *n, const char *s, void *unused) { (void)s; (void)unused; return n->reg ? n : NULL; }
static int of_property_read_bool(struct device_node *n, const char *s) { return !strcmp(s,"no-map") ? n->nomap : n->reusable; }
static struct reserved_mem *of_reserved_mem_lookup(struct device_node *n) { return n->found ? &n->r : NULL; }
static int of_address_to_resource(struct device_node *n, int i, struct resource *r) { (void)i; if (!n->static_ret) { r->start=0x100000; r->end=0x1fffff; r->flags=IORESOURCE_MEM; } return n->static_ret; }
'''
suffix = r'''
static void check(int condition) { if (!condition) abort(); }
int main(void) {
 struct device_node n={.reg=1}; struct resource r={0};
 check(!apple_ans_hmb_resource(&n,&r) && r.start==0x100000 && r.end==0x1fffff);
 n.static_ret=-EIO; check(apple_ans_hmb_resource(&n,&r)==-EIO);
 n=(struct device_node){.nomap=1,.found=1,.r={0x800000000ULL,0xe00000}};
 check(!apple_ans_hmb_resource(&n,&r) && r.start==n.r.base && r.end==n.r.base+n.r.size-1 && r.flags==IORESOURCE_MEM);
 n.nomap=0; check(apple_ans_hmb_resource(&n,&r)==-EINVAL); n.nomap=1;
 n.reusable=1; check(apple_ans_hmb_resource(&n,&r)==-EINVAL); n.reusable=0;
 n.found=0; check(apple_ans_hmb_resource(&n,&r)==-EINVAL); n.found=1;
 n.r.size=0; check(apple_ans_hmb_resource(&n,&r)==-EINVAL);
 n.r.base=UINT64_MAX-5; n.r.size=7; check(apple_ans_hmb_resource(&n,&r)==-EINVAL);
 puts("Fixed and dynamic HMB lookup guards passed."); return 0;
}
'''
with tempfile.TemporaryDirectory() as d:
    c = Path(d) / 'test.c'
    exe = Path(d) / 'test'
    c.write_text(prefix + body + suffix)
    subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', str(c), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
