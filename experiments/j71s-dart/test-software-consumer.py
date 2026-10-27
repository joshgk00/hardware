#!/usr/bin/env python3
"""Run the actual consumer probe against synthetic model/domain states."""
from pathlib import Path
import subprocess
import tempfile

source = Path(__file__).with_name('software-consumer.c').read_text()
start = source.index('static int j71s_dart_test_probe(')
end = source.index('\nstatic const struct of_device_id', start)
probe = source[start:end]
program = r'''
#include <errno.h>
struct device { int unused; };
struct platform_device { struct device dev; };
struct iommu_domain { unsigned int type; };
static int correct_model;
static struct iommu_domain *selected;
static int of_machine_is_compatible(const char *s) { (void)s; return correct_model; }
static struct iommu_domain *iommu_get_domain_for_dev(struct device *d) { (void)d; return selected; }
static int iommu_is_dma_domain(struct iommu_domain *d) { return !!(d->type & 2); }
#define dev_err_probe(dev, err, ...) ((void)(dev), (err))
#define dev_info(dev, ...) ((void)(dev))
''' + probe + r'''
int main(void) {
    struct platform_device p = {0};
    struct iommu_domain blocked = {0}, identity = {4}, dma = {3};
    correct_model = 0; selected = &dma;
    if (j71s_dart_test_probe(&p) != -ENODEV) return 1;
    correct_model = 1; selected = 0;
    if (j71s_dart_test_probe(&p) != -ENODEV) return 2;
    selected = &blocked;
    if (j71s_dart_test_probe(&p) != -ENODEV) return 3;
    selected = &identity;
    if (j71s_dart_test_probe(&p) != -ENODEV) return 4;
    selected = &dma;
    if (j71s_dart_test_probe(&p)) return 5;
    return 0;
}
'''
with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    (root / 'test.c').write_text(program)
    subprocess.run(['cc', '-std=c11', '-Wall', '-Werror', str(root / 'test.c'), '-o', str(root / 'test')], check=True)
    subprocess.run([str(root / 'test')], check=True)
print('Probe rejects wrong model, absent, blocked and identity domains; accepts a DMA domain')
