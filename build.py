#! /usr/bin/env python3

import argparse
from pathlib import Path
import subprocess
import sys
import scripts.templates
from scripts.templates import *
from scripts.scriptutil import load_db, load_json, dump_json, write_template, psyko
from operator import itemgetter

def cor_par(s):
  pars = s.split(',')
  pars[0] = int(pars[0])
  assert pars[0] in CORES, \
    f"The corunner id must be one of {CORES.join(', ')}"
  l = len(pars)
  if l > 2:
    raise argparse.ArgumentTypeError("Corunners parameters must be of type <core>,<start address of read>")
  elif l == 2:
    return pars
  else:
    return [pars[0], None]

def cor_cores(cors):
  return [i[0] for i in cors]

def getopts(argv):
    parser = argparse.ArgumentParser(description='Corunners builder')
    parser.add_argument("--psyko", "-P", type=Path,
                        help=Help.PSYKO, required=True)
    parser.add_argument("--kdbv", type=Path, required=True)
    parser.add_argument("--rtk-dir", "-K", type=Path,
                        help=Help.RTK_DIR, required=True)
    parser.add_argument("--product", "-p", type=str,
                        help=Help.PRODUCT,  required=True,
                        choices=[P2020,MPC5777M])
    parser.add_argument("--corunner", "-C", type=cor_par,
                        action="append", help=Help.CORUNNER, default=[])
    parser.add_argument("--task", "-T", type=str, choices=["H", "G"]+FLASHLIKE,
                        help=Help.TASK, required=True)
    parser.add_argument("--core", "-c", type=int, choices=CORES,
                        help=Help.CORE, required=True)
    parser.add_argument("--local-corunners", action='store_true',
                        help=Help.LOCAL_CORUNNERS)
    parser.add_argument("--build-dir", type=Path, default=TOP_DIR / "build",
                        help=Help.BUILD_DIR)
    parser.add_argument("--mem-conf", type=Path,
                        help=Help.MEM_CONF)
    parser.add_argument("--output", "-o", type=Path,
                        help=Help.OUTPUT)
    args = parser.parse_args(argv[1:])
    assert args.core not in cor_cores(args.corunner)
    if args.output is None:
        args.output = args.build_dir / "program.elf"
    return args

def gen_agent_config(output_filename, name, core):
    write_template(output_filename, AGENT_CONFIG_HJSON_TEMPLATE, {
        "agent_name": name,
        "agent_core": core,
    })

def gen_corunner_config(conf_filename, identifier, symbol, object_file, kmem_filename):
    write_template(conf_filename, CORUNNER_CONFIG_HJSON_TEMPLATE, {
        "corunner_id": identifier,
        "corunner_symbol": symbol,
        "corunner_object": str(object_file)
    })
    write_template(kmem_filename, CORUNNER_KMEMORY_JSON_TEMPLATE, {
        'symbol': symbol,
    })

def gen_corunner_source(output_filename, symbol, sram=dict()):
    cmd = [sys.executable, TOP_DIR / "scripts" / "gen-corunner.py", symbol]
    if sram:
        cmd += ["--sram"]
        if 'nop' in sram.keys():
          cmd += ["--nop", str(sram['nop'])]
        if 'start' in sram.keys():
          cmd += ["--startaddr", str(sram['start'])]
        if 'size' in sram.keys():
          cmd += ["--tablesize", str(sram['size'])]
        if 'stride' in sram.keys():
          cmd += ["--stride", str(sram['stride'])]
    else:
        cmd += ["--jump", "2048"]
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, universal_newlines=True) as proc:
        with open(output_filename, "w") as fileh:
            fileh.write(proc.stdout.read())

def gen_kmem_final(default, config, memreport, kdbv, tasks, corunners=list()):
    config_json = load_json(config)
    cmd = [sys.executable, TOP_DIR / 'scripts' / 'gen-kmem.py', '--config', config]
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

    ret = subprocess.Popen(cmd).wait()
    assert ret == 0

def get_sources(task_name):
    c_sources = [
        SRC_DIR / "crc.c",
        SRC_DIR / "filter.c",
        SRC_DIR / "filter2.c",
    ]
    psy_sources = [PSY_DIR / f"task_{task_name}.psy"]
    if task_name not in FLASHLIKE:
        c_sources += [
            STUBS_DIR / f"suite_task_{task_name}.c",
        ]
        psy_sources += [STUBS_DIR / f"for_task_{task_name}.psy"]
    return {
        "c": c_sources,
        "asm": [],
        "psy": psy_sources,
    }



def main(argv):
    args = getopts(argv)

    used_cores = cor_cores(args.corunner) + [args.core]
    args.corunner.sort(key=itemgetter(0))

    def object_of(source_filename, extension = ".o"):
        return args.build_dir / (source_filename.name + extension)

    sources = get_sources(args.task)

    ag_config = args.build_dir / "task.hjson"
    app_configs = [
        args.build_dir / "app.hjson",
        CFG_DIR / f"task_{args.task}.hjson",
        ag_config,
    ]
    tasks = [f'task_{args.task}']
    part_configs = []
    compile_config = args.build_dir / "compile.hjson"
    link_config = args.build_dir / "link.hjson"
    partition_config = args.build_dir / "partition.hjson"
    psymodule_config = args.build_dir / "psymodule.hjson"
    gen_agent_config(ag_config, f"task_{args.task}", args.core)
    mem_configs = []
    corunners = []
    for corunner,  cor_start in args.corunner:
        use_sram = bool(cor_start)
        sram_args = dict()
        co_config = args.build_dir / f"corunner_{corunner}.hjson"
        co_kmem = args.build_dir / f"corunner_{corunner}_kmem.json"
        co_file = args.build_dir / f"corunner_{corunner}"
        if use_sram:
            sram_args['start'] = cor_start
            sram_args['size'] = int(env.get(f"CORUNNER_READ_SIZE_{corunner}", "0x2000"), 16)
        symbol = f"co_runner_sram{corunner}" if sram_args else f"co_runner_flash{corunner}"
        co_file = co_file.with_suffix('.asm')
        sources["asm"].append(co_file)
        gen_corunner_source(co_file, symbol, sram_args)

        app_configs.append(co_config)
        mem_configs.append(co_kmem)
        corunners.append(symbol)
        gen_corunner_config(co_config, corunner, symbol, object_of(co_file), co_kmem)

    if args.task not in FLASHLIKE:
        stub_config = args.build_dir / "stub.hjson"
        gen_agent_config(stub_config, f"sends_to_task_{args.task}", args.core)
        app_configs.append(stub_config)
        tasks.append(f'sends_to_task_{args.task}')

  #  app_configs.append(link_config)

    write_template(compile_config, COMPILE_CONFIG_HJSON_TEMPLATE, {})
    write_template(psymodule_config, PSYMODULE_CONFIG_HJSON_TEMPLATE, {})
    write_template(link_config, LINK_CONFIG_HJSON_TEMPLATE, {})



    #==========================================================================
    # The functions below are just helpers to call the PsyC compiler psyko,
    # with a convenient access to global variables such as the path to the
    # compiler and the path to the RTK.
    psykonf = {'product': args.product, 'rtk_dir': args.rtk_dir, 'psyko': args.psyko, 'cwd': TOP_DIR}
    def psyko_cc(c_source):
        generated_object = object_of(c_source)
        psyko(psykonf, "cc", c_source, compile_config, "-o", generated_object)
        return generated_object

    def psyko_as(asm_source):
        generated_object = object_of(asm_source)
        psyko(psykonf, "as", asm_source, compile_config, "-o", generated_object)
        return generated_object

    def psyko_module(psy_source):
        generated_object = object_of(psy_source, ".psyo")
        psyko(psykonf, "module", psy_source, psymodule_config, "-o", generated_object)
        return generated_object

    def psyko_partition(name, objects, configs):
        generated_object = args.build_dir / (name + ".parto")
        psyko(psykonf, "partition", "-o", generated_object, '--gendir',
            args.build_dir / 'gen' / 'part', *objects, *configs)
        return generated_object

    def psyko_app(partos, configs):
        elf = args.build_dir / "program.elf"
        gendir = args.build_dir / "gen" / "app"
        psyko(psykonf, "app", "-a", args.build_dir / "program.app", "-b", args.output,
              '--gendir', gendir, *partos, *configs)
        return gendir
    def psyko_memconf(t, files, configs=list(), cor_kmems=list()):
        kmemconf = args.build_dir / ('kmemconf_'+t+'.json')
        psyko(psykonf, 'gen-mem-conf', '-t', t, '--gendir', args.build_dir / 'gen' / 'memconf', '-o', kmemconf, *files, *configs)

        if cor_kmems:
            def_memconf = load_json(kmemconf)
            cor_memconf = list()
            for kmem in cor_kmems:
                cor_memconf.append(load_json(kmem))
            max_reg = def_memconf['kmemory']['regions'][0]
            if len(def_memconf['kmemory']['regions']) > 1:
                for reg in def_memconf['kmemory']['regions'][1:]:
                    if reg['size'] > max_reg['size']:
                        max_reg = reg
            if 'domains' not in max_reg.keys():
                max_reg['domains'] = list()
                out = cor_memconf[0]['domains'][0]['output_sections'][0]
                out['physical_address'] = mar_reg['physical_address']
            stacks = {obj['id']: obj
                for obj in def_memconf['kmemory']['objects']
                if obj['id'] in [f"core_{core}_co_runner_stack.c"
                    for core in used_cores]}
            for core in cor_cores(args.corunner):
                stack = f"core_{core}_co_runner_stack.c"
                for corunner in corunners:
                   symbol = corunner if corunner[-1] == str(core) else ''

                stacks[stack]['groups'] = [f'.stack_{symbol}']

            for cor in cor_memconf:
                max_reg['domains'] += cor['domains']
                def_memconf['kmemory']['groups'] += cor['groups']
                def_memconf['kmemory']['objects'] += cor['objects']
            dump_json(def_memconf, f=kmemconf)

        return kmemconf

    #==========================================================================
    # Compile all the C, ASM and PsyC sources.
    # ASM sources are only present when co-runners are enabled.
    parto_objects = []
    for c_source in sources["c"]:
        parto_objects.append(psyko_cc(c_source))
    for asm_source in sources.get("asm", []):
        parto_objects.append(psyko_as(asm_source))
    for psy_source in sources["psy"]:
        parto_objects.append(psyko_module(psy_source))

    #==========================================================================
    # Generate a single partition, and then executable to be able to get the size of the sections
    parto = psyko_partition("main", parto_objects, part_configs)
    mem_configs = [psyko_memconf('app', [parto], app_configs, mem_configs)]
    mem_configs.append("--overwrite-memory-configuration")
    gendir = psyko_app([parto], app_configs+mem_configs)
    assert args.output.is_file(), "first app compilation not successfull"
    # Finally generate the final memory configs and the executable
    if args.mem_conf:
      args.output.unlink()
      gen_kmem_final(mem_configs[0], args.mem_conf,
          gendir / 'applink' / 'memreport_out.ks', args.kdbv, tasks, corunners)
      psyko_app([parto], app_configs+mem_configs)
      assert args.output.is_file(), "final app compilation not successfull"

if __name__ == "__main__":
    main(sys.argv)
