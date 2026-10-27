#!/usr/bin/env python3
"""Add a J71s battery-pin configuration log before Linux applies its mux."""
import hashlib
from pathlib import Path
import sys


def main(root):
    path = root / 'drivers/pinctrl/pinctrl-apple-gpio.c'
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != '9e387713c4443d0af50fde108ae46d35e2f57adc2738c005b3de5bf8d4c7533c':
        raise ValueError('Unexpected pinctrl source')
    before = ('\tstruct apple_gpio_pinctrl *pctl = pinctrl_dev_get_drvdata(pctldev);\n\n'
              '\tapple_gpio_set_reg(\n')
    after = ('\tstruct apple_gpio_pinctrl *pctl = pinctrl_dev_get_drvdata(pctldev);\n\n'
             '\tif (group == 2 && (func == 1 || func == 2) &&\n'
             '\t    !strcmp(dev_name(pctl->dev), "20f100000.pinctrl")) {\n'
             '\t\tu32 before = apple_gpio_get_reg(pctl, group);\n'
             '\t\tdev_info(pctl->dev, "experimental HDQ pin before mux: function=%u input=%u pull=%u\\n",\n'
             '\t\t\t (unsigned int)FIELD_GET(REG_GPIOx_PERIPH, before),\n'
             '\t\t\t !!(before & REG_GPIOx_INPUT_ENABLE),\n'
             '\t\t\t (unsigned int)FIELD_GET(REG_GPIOx_PULL, before));\n'
             '\t}\n\n\tapple_gpio_set_reg(\n')
    text = data.decode('utf-8')
    if text.count(before) != 1:
        raise ValueError('Unexpected pinctrl source layout')
    path.write_text(text.replace(before, after, 1), encoding='utf-8')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python log-pin-before-mux.py KERNEL_CHECKOUT')
    main(Path(sys.argv[1]))
