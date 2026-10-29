#!/usr/bin/env python3
"""Test the actual machine/opt-in helpers in the experimental NVMe patch."""
from pathlib import Path
import subprocess
import tempfile
patch = Path(__file__).with_name('j71s-nvme-readonly-guard.patch').read_text()
added = '\n'.join(x[1:] for x in patch.splitlines() if x.startswith('+') and not x.startswith('+++'))
def function(name):
    start = added.index('static bool ' + name + '(')
    return added[start:added.index('\n}', start) + 2]
helpers = function('nvme_apple_legacy_diagnostic') + '\n' + function('nvme_legacy_opt_in_valid')
assert 'if (!nvme_legacy_opt_in_valid())' in added
assert '!nvme_legacy_opt_in_valid() || pdev->vendor' in added
assert 'nvme_apple_legacy_diagnostic() &&' in added
prefix = r'''
#include <stdbool.h>
#include <string.h>
#include <stdlib.h>
static bool j71s_ro_test, j71b_ro_test, j71b_rw;
static int model;
static bool of_machine_is_compatible(const char *s) {
 return (!strcmp(s,"apple,j71s") && model==5) || (!strcmp(s,"apple,j71b") && model==6);
}
'''
suffix = r'''
int main(void) {
 for (model=0;model<=6;model++) for(int bits=0;bits<8;bits++) {
  j71s_ro_test=bits&1;j71b_ro_test=bits&2;j71b_rw=bits&4;
  bool diagnostic=model==5||model==6;
  bool allowed=model==5?(bits==1):model==6?(bits==2||bits==4):true;
  if (nvme_apple_legacy_diagnostic()!=diagnostic || nvme_legacy_opt_in_valid()!=allowed) abort();
 }
}
'''
with tempfile.TemporaryDirectory() as d:
    p=Path(d); (p/'test.c').write_text(prefix+helpers+suffix)
    subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(p/'test.c'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True)
print('iPad 5 read-only opt-in and iPad 6 mode matrix passed.')
