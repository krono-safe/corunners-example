#! /bin/env python3

from products.P2020_ds import P2020_ds
from utils.templates import TOP_DIR
import utils.templates as globs
from utils.scriptutil import run_cmd

FLASHLIKE = ['FLASH', 'U']
test = P2020_ds()
task = 'U'
core = 1
ag = [f'task_{task}']
if task not in FLASHLIKE:
    ag.append(f'sends_to_task_{task}')
globs.KBG_JSON = globs.APP_DIR / f'kbuildgen_{task}.json'
pgrms = {}
pgrms['coff'] = test.build(task, 'test_main_cOFF', core, agents=ag, max_mes=512)
pgrms['con'] =  test.build(task, 'test_main_cON', core, agents=ag, max_mes=512,
                  corunner={
                            'type': 'read',
                            'read': '0x20000000',
                            'size': 0x2000
                            })
def exec_pgrm(p):
    print(pgrms[p])
    f = test.genCmm({'app_elf': [pgrms[p]], 'core': core})
    fname = f.name
    print(fname)
    cmd = ['t32/trunner', fname, f'output/{p}.bin', 'output/times.log']
    run_cmd(cmd, TOP_DIR, name='trunner', timeout=None)
exec_pgrm('coff')
exec_pgrm('con')
#input()
