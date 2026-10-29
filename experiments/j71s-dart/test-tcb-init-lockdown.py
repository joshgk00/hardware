#!/usr/bin/env python3
"""Check the one-shot diagnostic patch retains its coupled restart guards."""
from pathlib import Path
patch = Path(__file__).with_name('tcb-init-local-lockdown.patch').read_text()
helper = (Path(__file__).parent / 'driver-patch/j71s-tcb-init-test.h').read_text()
added = '\n'.join(line[1:] for line in patch.splitlines()
                  if line.startswith('+') and not line.startswith('+++'))
required = (
    'static int kexec_load_disabled = 1;',
    'return kexec_load_disabled == 1 && !kexec_image && !kexec_crash_image;',
    'bool j71s_test_kexec_locked(void);',
    '.suppress_bind_attrs = true',
    '#include "j71s-tcb-init-test.h"',
    'j71s_test_tcb_init(pdev, data->bar, host->dev.parent);',
)
for item in required:
    if item not in added:
        raise SystemExit('Missing lockdown integration: ' + item)
if helper.count('j71s_test_kexec_locked()') != 2:
    raise SystemExit('Expected kexec guard at entry and before arming')
arm=helper.index('armed = true;')
retain=helper.index('retained = true;', arm)
command=helper.index('writel(0x10000, mmu + 0x04);', arm)
if not arm < retain < command:
    raise SystemExit('Buffer retention must be set before the init command')
print('One-shot kexec, unbind, arming and buffer-retention integration checks passed.')
