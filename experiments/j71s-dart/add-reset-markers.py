#!/usr/bin/env python3
"""Add model-guarded progress logs around DART0 reset in a test kernel."""
import hashlib
from pathlib import Path
import sys

EXPECTED = '68740d3c74ba9bda8acc0582df1a6b547e1f894057aaa2afecab85a41e03e7d1'
OLD = '''\tret = apple_dart_hw_reset(dart);
\tif (ret)
\t\tgoto err_clk_disable;

\tret = request_irq(dart->irq, dart->hw->irq_handler, IRQF_SHARED,
'''
NEW = '''\tif (of_machine_is_compatible("apple,j71s") &&
\t    !strcmp(dev_name(dev), "601008000.iommu"))
\t\tdev_info(dev, "experimental DART0: about to reset controller\\n");
\tret = apple_dart_hw_reset(dart);
\tif (ret)
\t\tgoto err_clk_disable;
\tif (of_machine_is_compatible("apple,j71s") &&
\t    !strcmp(dev_name(dev), "601008000.iommu"))
\t\tdev_info(dev, "experimental DART0: reset returned\\n");

\tret = request_irq(dart->irq, dart->hw->irq_handler, IRQF_SHARED,
'''


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit('Usage: add-reset-markers.py KERNEL_CHECKOUT')
    source = Path(sys.argv[1]) / 'drivers/iommu/apple-dart.c'
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED:
        raise SystemExit('Unexpected DART source; refusing to patch')
    text = raw.decode('utf-8')
    if text.count(OLD) != 1:
        raise SystemExit('Reset insertion point is not unique')
    source.write_text(text.replace(OLD, NEW, 1))
    print('Added J71s DART0 reset markers; hardware behavior is unchanged')


if __name__ == '__main__':
    main()
