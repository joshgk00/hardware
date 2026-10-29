#!/usr/bin/env python3
"""Check that only the isolated, armed one-shot may enable bus mastering."""
from pathlib import Path
import subprocess,tempfile
src=(Path(__file__).parent/'driver-patch/j71s-identify-master-policy.h').read_text()
fn=src[src.index('static bool'):]
preamble='''#include <stdbool.h>\n#include <stdint.h>\n#include <stdlib.h>\ntypedef uint32_t u32;typedef uint16_t u16;\n#define PCI_COMMAND 4\n#define PCI_COMMAND_MEMORY 2\n#define PCI_COMMAND_MASTER 4\n#define PCI_COMMAND_INTX_DISABLE 1024\n'''
test=r'''
#define CALL(opt,used,armed,pub,scratch,lock,bus,dev,off,sz,id,cur,req) j71s_identify_master_allowed(opt,used,armed,pub,scratch,lock,bus,dev,off,sz,id,cur,req)
int main(void){
 if(!CALL(1,0,1,1,1,1,1,0,4,2,0x2002106b,2,6))abort();
 if(!CALL(1,0,1,1,1,1,1,0,4,2,0x2002106b,1026,1030))abort();
 if(CALL(0,0,1,1,1,1,1,0,4,2,0x2002106b,2,6)||CALL(1,1,1,1,1,1,1,0,4,2,0x2002106b,2,6)||
 CALL(1,0,0,1,1,1,1,0,4,2,0x2002106b,2,6)||CALL(1,0,1,0,1,1,1,0,4,2,0x2002106b,2,6)||
 CALL(1,0,1,1,0,1,1,0,4,2,0x2002106b,2,6)||CALL(1,0,1,1,1,0,1,0,4,2,0x2002106b,2,6)||
 CALL(1,0,1,1,1,1,0,0,4,2,0x2002106b,2,6)||CALL(1,0,1,1,1,1,1,1,4,2,0x2002106b,2,6)||
 CALL(1,0,1,1,1,1,1,0,5,2,0x2002106b,2,6)||CALL(1,0,1,1,1,1,1,0,4,4,0x2002106b,2,6)||
 CALL(1,0,1,1,1,1,1,0,4,2,0x12345678,2,6)||CALL(1,0,1,1,1,1,1,0,4,2,0x2002106b,0,4)||
 CALL(1,0,1,1,1,1,1,0,4,2,0x2002106b,6,6)||CALL(1,0,1,1,1,1,1,0,4,2,0x2002106b,2,7)||
 CALL(1,0,1,1,1,1,1,0,4,2,0x2002106b,2,2))abort();
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'test.c').write_text(preamble+fn+test)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('One-shot PCI bus-master write policy passed.')
