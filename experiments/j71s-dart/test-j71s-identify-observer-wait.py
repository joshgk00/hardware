#!/usr/bin/env python3
"""Exercise the actual bounded observer wait without real sleeping."""
from pathlib import Path
import subprocess,tempfile
src=(Path(__file__).parent/'driver-patch/j71s-identify-observer-wait.h').read_text()
fn=src[src.index('static bool'):]
preamble=r'''
#include <stdbool.h>
#include <stdlib.h>
#define READ_ONCE(x) (x)
static bool gate;static int sleeps,signal_at;
static void msleep(unsigned n){if(n!=100)abort();sleeps++;if(signal_at && sleeps==signal_at)gate=true;}
'''
test=r'''
int main(void){
 if(j71s_identify_wait_observer(NULL,5))abort();
 gate=true;sleeps=0;if(!j71s_identify_wait_observer(&gate,10)||sleeps)abort();
 gate=false;sleeps=0;signal_at=0;if(j71s_identify_wait_observer(&gate,5)||sleeps!=5)abort();
 gate=false;sleeps=0;signal_at=3;if(!j71s_identify_wait_observer(&gate,10)||sleeps!=3)abort();
 gate=false;sleeps=0;signal_at=1;if(j71s_identify_wait_observer(&gate,0)||sleeps)abort();
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'test.c').write_text(preamble+fn+test)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('Observer wait immediate, delayed, timeout and null cases passed.')
