#!/usr/bin/env python3
"""Prepare the published S5L UCON bit-preservation test and a boot probe.

The bit-preservation change follows Yureka Lilian's Linux patch:
https://lists.openwall.net/linux-kernel/2026/10/02/2066
The additional boot log is specific to this experimental J71s UART.
Run after prepare-j71s-hdq.sh and add-hdq-debug.py, on a separate checkout.
"""
import hashlib
from pathlib import Path
import sys


def main(root):
    header = root / 'include/linux/serial_s3c.h'
    serial = root / 'drivers/tty/serial/samsung_tty.c'
    expected = {
        header: 'cc193c87e07954eb32e81b2867fcdaccac5c29cf62919a13b19a99eda62e175d',
        serial: '83d2cf2b67aa10c03c3463f1a1462574f388a6accfb9639aeee2bc72be4562b6',
    }
    sources = {}
    for path, digest in expected.items():
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError('Unexpected source: ' + str(path))
        sources[path] = data.decode('utf-8')

    def change(text, old, new):
        if text.count(old) != 1:
            raise ValueError('Unexpected UART source layout')
        return text.replace(old, new, 1)

    h = sources[header]
    h = change(h, '#define APPLE_S5L_UCON_RXTO_ENA\t\t\t9\n',
               '#define APPLE_S5L_UCON_RXTO_ENA\t\t\t9\n#define APPLE_S5L_UCON_UNK\t\t\t10\n')
    h = change(h, '#define APPLE_S5L_UCON_RXTO_ENA_MSK\t\tBIT(APPLE_S5L_UCON_RXTO_ENA)\n',
               '#define APPLE_S5L_UCON_RXTO_ENA_MSK\t\tBIT(APPLE_S5L_UCON_RXTO_ENA)\n'
               '#define APPLE_S5L_UCON_UNK_MSK\t\t\tBIT(APPLE_S5L_UCON_UNK)\n')
    h = change(h, '#define APPLE_S5L_UCON_MASK\t\t(APPLE_S5L_UCON_RXTO_ENA_MSK | \\\n',
               '#define APPLE_S5L_UCON_MASK\t\t(APPLE_S5L_UCON_RXTO_ENA_MSK | \\\n'
               '\t\t\t\t\t APPLE_S5L_UCON_UNK_MSK | \\\n')
    s = change(sources[serial], '\tu32 ucon = rd_regl(port, S3C2410_UCON);\n\n'
               '\tucon &= (info->clksel_mask | info->ucon_mask);',
               '\tu32 ucon = rd_regl(port, S3C2410_UCON);\n\n'
               '\tif (port->mapbase == 0x20a0d4000ULL)\n'
               '\t\tdev_info(port->dev, "experimental HDQ boot UART control bit10=%u\\n",\n'
               '\t\t\t !!(ucon & BIT(10)));\n\n'
               '\tucon &= (info->clksel_mask | info->ucon_mask);')
    header.write_text(h, encoding='utf-8')
    serial.write_text(s, encoding='utf-8')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python preserve-ucon.py PREPARED_DEBUG_KERNEL_CHECKOUT')
    main(Path(sys.argv[1]))
