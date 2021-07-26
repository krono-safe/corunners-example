#! /usr/bin/env python3

import argparse
from pathlib import Path
from os import environ as env
import sys
import subprocess
from operator import itemgetter
from utils.templates import TOP_DIR, CORUNNER_KMEMORY_JSON_TEMPLATE
import utils.templates as globs
from utils.scriptutil import load_json, dump_json, write_template, run_cmd
from utils.gen_corunner import read_cor, jump_cor


def ninja(build_dir, target='', name=''):
    if name:
        name = f"ninja_{name}"
    else:
        name = ninja
    cmd = ['ninja', '-f', str(build_dir / 'gen/build.ninja'), target]
    while not run_cmd(cmd, globs.APP_DIR, name=name):
        pass


def object_of(source_filename, build_dir, extension=".o"):
    return build_dir / (source_filename.name + extension)


def get_corunner(core: int, t: str) -> str:
    """
    returns the symbol of the corunner and the name of the object file
    """
    return f"co_runner_{t.lower()}{core}", f"corunner_{core}"


def cor_cores(cors):
    """
    Takes a list returned by corunner_to_list and returns a list containing
    only the cores in the same order (to know which cores are used).
    """
    return [i[0] for i in cors]


def gen_corunner_config(symbol, kmem_filename):
    write_template(kmem_filename, CORUNNER_KMEMORY_JSON_TEMPLATE, {
        'symbol': symbol,
    })


def gen_kmem_final(default, config, memreport, kdbv, tasks, corunners=[]):
    config_json = load_json(config)
    cmd = [sys.executable, TOP_DIR / 'scripts' / 'gen-kmem.py', '--config',
           config]
    del_list = []
    config_json['memreport'] = str(memreport)
    config_json['default_kmemory'] = str(default)
    for el in config_json['elements']:
        if el['type'] == 'corunner':
            if corunners:
                el['names'] = corunners
            else:
                del_list.append(el)
        elif el['type'] == 'task':
            el['names'] = tasks
        else:
            del_list.append(el)
    for el in del_list:
        config_json['elements'].remove(el)

    dump_json(config_json, config)

    ret = subprocess.check_call(cmd)


def doBuild(task, core, build_dir, max_mes, kbuildgen_bin, kbg_json=None,
            mem_conf={}, corunner_list=[], local_corunner=False):
    if kbg_json is None:
        kbg_json = build_dir / 'kbuildgen.json'
    kbg = load_json(kbg_json)

    mem_configs = []
    corunners = []

    output = Path(kbg['output_binary'])
    gendir = Path(kbg['psyko_options']['gen_dir']) / 'app_gendir'

    if corunner_list:
        used_cores = cor_cores(corunner_list) + [core]
        corunner_list.sort(key=itemgetter(0))

    for corunner,  cor_start, cor_size in corunner_list:
        # The read corunner is created only if a start address si provided for
        # this corunner.
        use_read = bool(cor_start)
        read_args = {}
        co_config = build_dir / f"corunner_{corunner}.hjson"
        co_kmem = build_dir / f"corunner_{corunner}_kmem.json"
        co_file = build_dir / f"corunner_{corunner}.asm"
        corunner_content = ''
        co_symbol = ''
        if use_read:
            if cor_size is None:
                cor_size = 0x2000
            co_symbol = f"co_runner_read{corunner}"
            corunner_content = read_cor(
                                            co_symbol,
                                            startaddr=cor_start,
                                            tablesize=cor_size
                                       )
        else:
            if cor_size is None:
                cor_size = 2048
            co_symbol = f"co_runner_flash{corunner}"
            corunner_content = jump_cor(co_symbol, jumps=cor_size)
        with open(co_file, "w") as fileh:
            fileh.write(corunner_content)

        mem_configs.append(co_kmem)
        corunners.append(co_symbol)
        gen_corunner_config(co_symbol, co_kmem)

    # =========================================================================
    # The functions below are just helpers to call the PsyC compiler psyko,
    # with a convenient access to global variables such as the path to the
    # compiler and the path to the RTK.
    psykonf = {
        'product': kbg['psyko_options']['product'],
        'rtk_dir': kbg['psyko_options']['kernel_dir'],
        'psyko': kbg['psyko'],
        'cwd': TOP_DIR,
        'build_dir': str(build_dir / 'gen')
    }
    kmemconf = kbg['kmemory']

    def kbuildgen():
        cmd = ['python3', str(kbuildgen_bin)]
        cmd += ['--source-dir', psykonf['build_dir']]
        cmd += ['--build-dir', str(build_dir / 'build')]
        cmd += ['--gen-build', 'ninja']
        cmd += [str(kbg_json)]
        while not run_cmd(cmd, psykonf['cwd'], name='kbuildgen'):
            pass

    def psyko_memconf(cor_kmems=[]):
        """
        This function generates a valid default memconf used to perform the
        first compilation. It creates a default kmemory for the task and adds
        the configs for all the corunners.
        """
        ninja(build_dir, target='kmemconf_json_alias', name='kmemconf')

        if cor_kmems:
            def_memconf = load_json(kmemconf)
            cor_memconf = []
            for kmem in cor_kmems:
                cor_memconf.append(load_json(kmem))
            max_reg = def_memconf['kmemory']['regions'][0]
            if len(def_memconf['kmemory']['regions']) > 1:
                for reg in def_memconf['kmemory']['regions'][1:]:
                    if reg['size'] > max_reg['size']:
                        max_reg = reg
            if 'domains' not in max_reg:
                max_reg['domains'] = []
                out = cor_memconf[0]['domains'][0]['output_sections'][0]
                out['physical_address'] = mar_reg['physical_address']
            stacks = {
                          obj['id']: obj
                          for obj in def_memconf['kmemory']['objects']
                          if obj['id'] in [f"core_{core}_co_runner_stack.c"
                                           for core in used_cores]
                      }
            for core in cor_cores(corunner_list):
                stack = f"core_{core}_co_runner_stack.c"
                for corunner in corunners:
                    symbol = corunner if corunner[-1] == str(core) else ''

                stacks[stack]['groups'] = [f'.stack_{symbol}']

            for cor in cor_memconf:
                max_reg['domains'] += cor['domains']
                def_memconf['kmemory']['groups'] += cor['groups']
                def_memconf['kmemory']['objects'] += cor['objects']
            dump_json(def_memconf, f=kmemconf)

    # =========================================================================
    # Generate a single partition, and then executable to be able to get the
    # size of the sections
    env['STUBBORN_MAX_MEASURES'] = str(max_mes)
    kbuildgen()
    psyko_memconf(mem_configs)
    ninja(build_dir, target='program_elf_alias', name='app')
    assert output.is_file(), "first app compilation not successfull"
    # Finally generate the final memory configs and the executable
    if mem_conf:
        output.unlink()
        gen_kmem_final(mem_configs[0], mem_conf,
                       gendir / 'applink' / 'memreport_out.ks', kdbv, tasks,
                       corunners)
        ninja(build_dir, name='app_placed')
        assert output.is_file(), "final app compilation not successfull"
