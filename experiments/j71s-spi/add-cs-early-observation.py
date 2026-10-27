#!/usr/bin/env python3
"""Add a read-only GPIO102 configuration log at pinctrl probe on J71s."""
import hashlib
from pathlib import Path
import sys

EXPECTED = '2fde8a8ece3ab8de33b061a99dc0ad18d17a569cad59c0630c50f391d7711ac5'
ANCHOR = '''\tfor (i = 0; i < npins; i++) {
\t\tpins[i].number = i;
'''
INSERT = '''\t/* J71s experiment: observe CS pin before pinctrl registration. */
\tif (npins > 102 && of_machine_is_compatible("apple,j71s") &&
\t    !strcmp(dev_name(pctl->dev), "20f100000.pinctrl")) {
\t\tu32 before;
\t\tint err = regmap_read(pctl->map, REG_GPIO(102), &before);

\t\tif (err)
\t\t\tdev_warn(pctl->dev, "experimental SPI3 CS early read failed: %d\\n", err);
\t\telse
\t\t\tdev_info(pctl->dev, "experimental SPI3 CS early: function=%u input=%u pull=%u\\n",
\t\t\t\t (unsigned int)FIELD_GET(REG_GPIOx_PERIPH, before),
\t\t\t\t !!(before & REG_GPIOx_INPUT_ENABLE),
\t\t\t\t (unsigned int)FIELD_GET(REG_GPIOx_PULL, before));
\t}

'''


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit('Usage: add-cs-early-observation.py KERNEL_CHECKOUT')
    source = Path(sys.argv[1]) / 'drivers/pinctrl/pinctrl-apple-gpio.c'
    data = source.read_bytes()
    if hashlib.sha256(data).hexdigest() != EXPECTED:
        raise SystemExit('Unexpected pinctrl source; refusing to patch')
    text = data.decode('utf-8')
    if text.count(ANCHOR) != 1:
        raise SystemExit('Pinctrl insertion point is not unique')
    source.write_text(text.replace(ANCHOR, INSERT + ANCHOR, 1))
    print('Added J71s-only read-only early pin observation')


if __name__ == '__main__':
    main()
