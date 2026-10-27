#!/usr/bin/env python3
"""Count HDQ symbols on which the current decoder and TI example disagree.

This diagnostic does not change decoded results or print raw gauge values.
Run after prepare-j71s-hdq.sh and add-hdq-debug.py on a separate checkout.
"""
import hashlib
from pathlib import Path
import sys


def main(root):
    path = root / 'drivers/w1/masters/w1-uart.c'
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != '9841dd764c32f814074d2f1edad76b89006e74940701099c2d0bc3bd42acea6f':
        raise ValueError('Unexpected HDQ source')
    text = data.decode('utf-8')

    def change(old, new):
        nonlocal text
        if text.count(old) != 1:
            raise ValueError('Unexpected HDQ source layout')
        text = text.replace(old, new, 1)

    change(' * @hdq_rx_bit: number of accepted echo and response symbols\n',
           ' * @hdq_rx_bit: number of accepted echo and response symbols\n'
           ' * @hdq_ambiguous: response symbols decoded differently by the TI example\n')
    change('\tu8 hdq_rx_bit;\n', '\tu8 hdq_rx_bit;\n\tu8 hdq_ambiguous;\n')
    change('\tw1dev->hdq_rx_bit = 0;\n',
           '\tw1dev->hdq_rx_bit = 0;\n\tw1dev->hdq_ambiguous = 0;\n')
    change('\tret = 0;\n\tgoto deselect_mux;',
           '\tspin_lock_irqsave(&w1dev->hdq_rx_lock, flags);\n'
           '\tbit = w1dev->hdq_ambiguous;\n'
           '\tspin_unlock_irqrestore(&w1dev->hdq_rx_lock, flags);\n'
           '\tdev_dbg(&serdev->dev, "experimental HDQ ambiguous response symbols=%u\\n", bit);\n'
           '\tret = 0;\n\tgoto deselect_mux;')
    change('\t\t\tif (w1dev->hdq_rx_bit >= W1_UART_HDQ_BITS_PER_BYTE &&\n'
           '\t\t\t    buf[i] >= W1_UART_HDQ_RX_ONE_MIN)',
           '\t\t\tif (w1dev->hdq_rx_bit >= W1_UART_HDQ_BITS_PER_BYTE &&\n'
           '\t\t\t    buf[i] >= 0xf0 && buf[i] <= 0xf8)\n'
           '\t\t\t\tw1dev->hdq_ambiguous++;\n\n'
           '\t\t\tif (w1dev->hdq_rx_bit >= W1_UART_HDQ_BITS_PER_BYTE &&\n'
           '\t\t\t    buf[i] >= W1_UART_HDQ_RX_ONE_MIN)')
    path.write_text(text, encoding='utf-8')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python add-hdq-ambiguity.py PREPARED_KERNEL_CHECKOUT')
    main(Path(sys.argv[1]))
