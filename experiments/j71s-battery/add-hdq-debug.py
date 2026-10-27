#!/usr/bin/env python3
"""Add temporary dynamic-debug probes to an already prepared HDQ checkout.

The probes report UART interrupt status and a receive-byte count, not battery
contents. They are disabled until dynamic debug is explicitly enabled.
"""
import hashlib
from pathlib import Path
import sys


CHANGES = {
    'drivers/tty/serial/samsung_tty.c': (
        '0a3122c8045fa1750869f8aecf39513254b6c43014f8b3cab53ebb7eea542737',
        '\tirqreturn_t ret = IRQ_NONE;\n\n\tif (pend & (APPLE_S5L_UTRSTAT_RXTHRESH',
        '\tirqreturn_t ret = IRQ_NONE;\n\n'
        '\tdev_dbg_ratelimited(port->dev, "experimental UART IRQ status %#x\\n", pend);\n\n'
        '\tif (pend & (APPLE_S5L_UTRSTAT_RXTHRESH',
    ),
    'drivers/w1/masters/w1-uart.c': (
        '89d79564e3a1c63ee45ab03abcc7b688b2256a4f3e9cf443dda009a77d26c5aa',
        '\t\t\t\t\t      W1_UART_TIMEOUT);\n\tif (!timeout) {\n\t\tret = -ETIMEDOUT;',
        '\t\t\t\t\t      W1_UART_TIMEOUT);\n\tif (!timeout) {\n'
        '\t\tunsigned int received;\n\n'
        '\t\tspin_lock_irqsave(&w1dev->hdq_rx_lock, flags);\n'
        '\t\treceived = w1dev->hdq_rx_bit;\n'
        '\t\tspin_unlock_irqrestore(&w1dev->hdq_rx_lock, flags);\n'
        '\t\tdev_dbg(&serdev->dev, "experimental HDQ timeout after %u received bits\\n", received);\n'
        '\t\tret = -ETIMEDOUT;',
    ),
}


def main(root):
    updates = []
    for relative, (expected, before, after) in CHANGES.items():
        path = root / relative
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('Unexpected HDQ source: ' + relative)
        text = data.decode('utf-8')
        if text.count(before) != 1:
            raise ValueError('Unexpected diagnostic insertion point: ' + relative)
        updates.append((path, text.replace(before, after, 1)))
    for path, text in updates:
        path.write_text(text, encoding='utf-8')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python add-hdq-debug.py PREPARED_KERNEL_CHECKOUT')
    main(Path(sys.argv[1]))
