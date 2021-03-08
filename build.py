#! /usr/bin/env python3

import argparse
import os
from pathlib import Path
from string import Template
import subprocess
import sys

TOP_DIR = Path(__file__).parent.resolve()
PSY_DIR = TOP_DIR / "psy"
SRC_DIR = TOP_DIR / "src"
CFG_DIR = TOP_DIR / "config"
STUBS_DIR = TOP_DIR / "psy" / "stubs"

AGENT_CONFIG_HJSON_TEMPLATE = """
{
    app: {
        agents: [
            {
                name: $agent_name
                core: $agent_core
            }
        ]
    }
}
"""

CORUNNER_CONFIG_HJSON_TEMPLATE = """
{
    app: {
        cores: [
            {
                id: ${corunner_id}
                co_runner: {
                    symbol: ${corunner_symbol}
                    object: ${corunner_object}
                }
            }
        ]
    }
}
"""

COMPILE_CONFIG_HJSON_TEMPLATE = """
{
    compile: {
        cflags: [
            "-g2",
            "-Xdebug-dwarf2",
            "-Xdebug-local-cie",
            "-Xdialect-c99",
            "-X230=1",
            "-X43=0", # Do not insert eieio !
            """ + f'''"-I", "{TOP_DIR}/include",''' + """
        ]
    }
}
"""

PSYMODULE_CONFIG_HJSON_TEMPLATE = """
{
    psymodule: {
        psy_pp_flags: [
            "-I", "include",
        ]
        cflags: [
            "-g2",
            "-Xdebug-dwarf2",
            "-Xdebug-local-cie",
            "-Xdialect-c99",
            "-X230=1",
            "-X43=0", # Do not insert eieio !!
            """ + f'''"-I", "{TOP_DIR}/include",''' + """
        ]
    }
}
"""

class Help:
    RTK_DIR = "Path to the ASTERIOS RTK"
    CORUNNER_ID = "ID of the co-runner to enable; can be specified multiple times"
    TASK = "Name of the nominal task to be compiled for execution"
    PSYKO = "Path to the PsyC Compiler psyko"
    BUILD_DIR = "Path to the build directory in which artifacts are produced"
    CORE = "ID of the core on which the task will run; must not conflict with --corunner-id"
    LOCAL_CORUNNERS = "If set, co-runners will be configured to only access local memories"
    OUTPUT = "Path where the executable is to be generated"
    PRODUCT = "Name of the ASTERIOS RTK Product"

def getopts(argv):
    parser = argparse.ArgumentParser(description='Corunners builder')
    parser.add_argument("--psyko", "-P", type=Path,
                        help=Help.PSYKO, required=True)
    parser.add_argument("--rtk-dir", "-K", type=Path,
                        help=Help.RTK_DIR, required=True)
    parser.add_argument("--product", "-p", type=str,
                        help=Help.PRODUCT, default="power-mpc5777m-evb")
    parser.add_argument("--corunner-id", "-C", type=int, choices=[0, 1, 2],
                        action="append", help=Help.CORUNNER_ID, default=[])
    parser.add_argument("--task", "-T", type=str, choices=["H", "G", "FLASH"],
                        help=Help.TASK, required=True)
    parser.add_argument("--core", "-c", type=int, choices=[0, 1, 2],
                        help=Help.CORE, required=True)
    parser.add_argument("--local-corunners", action='store_true',
                        help=Help.LOCAL_CORUNNERS)
    parser.add_argument("--build-dir", type=Path, default=TOP_DIR / "build",
                        help=Help.BUILD_DIR)
    parser.add_argument("--output", "-o", type=Path,
                        help=Help.OUTPUT)
    args = parser.parse_args(argv[1:])
    assert not args.core in args.corunner_id
    if args.output is None:
        args.output = args.build_dir / "program.elf"
    return args


def write_template(output_filename, template, context):
    output_filename.parent.mkdir(exist_ok=True, parents=True)
    with open(output_filename, "w") as fileh:
        fileh.write(Template(template).substitute(context))


def gen_agent_config(output_filename, name, core):
    write_template(output_filename, AGENT_CONFIG_HJSON_TEMPLATE, {
        "agent_name": name,
        "agent_core": core,
    })


def gen_corunner_config(output_filename, identifier, symbol, object_file):
    write_template(output_filename, CORUNNER_CONFIG_HJSON_TEMPLATE, {
        "corunner_id": identifier,
        "corunner_symbol": symbol,
        "corunner_object": str(object_file)
    })


def gen_corunner_source(output_filename, symbol, *, sram=False):
    cmd = [sys.executable, TOP_DIR / "scripts" / "gen-corunner.py", symbol]
    if sram:
        cmd += ["--sram"]
    else:
        cmd += ["--jump", "2048"]
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, universal_newlines=True) as proc:
        with open(output_filename, "w") as fileh:
            fileh.write(proc.stdout.read())

def get_sources(task_name):
    c_sources = [
        SRC_DIR / "crc.c",
        SRC_DIR / "filter.c",
        SRC_DIR / "filter2.c",
    ]
    asm_sources = []
    psy_sources = [PSY_DIR / f"task_{task_name}.psy"]
    if task_name != "FLASH":
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

    def object_of(source_filename, extension = ".o"):
        return args.build_dir / (source_filename.name + extension)

    hjson_conf_file = "app."+args.product+".hjson"

    sources = get_sources(args.task)

    ag_config = args.build_dir / "task.hjson"
    app_configs = [
        CFG_DIR / hjson_conf_file,
        CFG_DIR / f"task_{args.task}.hjson",
        ag_config,
    ]

    compile_config = args.build_dir / "compile.hjson"
    psymodule_config = args.build_dir / "psymodule.hjson"
    gen_agent_config(ag_config, f"task_{args.task}", args.core)
    for corunner in args.corunner_id:
        co_config = args.build_dir / f"corunner_{corunner}.hjson"
        co_obj = args.build_dir / f"corunner_{corunner}.asm"
        use_sram = corunner == 0
        symbol = f"co_runner_sram{corunner}" if use_sram else f"co_runner_flash{corunner}"
        app_configs.append(co_config)
        sources["asm"].append(co_obj)
        gen_corunner_config(co_config, corunner, symbol, object_of(co_obj))
        gen_corunner_source(co_obj, symbol, sram=use_sram)

    if args.task != "FLASH":
        stub_config = args.build_dir / "stub.hjson"
        gen_agent_config(stub_config, f"sends_to_task_{args.task}", args.core)
        app_configs.append(stub_config)

    write_template(compile_config, COMPILE_CONFIG_HJSON_TEMPLATE, {})
    write_template(psymodule_config, PSYMODULE_CONFIG_HJSON_TEMPLATE, {})



    #==========================================================================
    # The functions below are just helpers to call the PsyC compiler psyko,
    # with a convenient access to global variables such as the path to the
    # compiler and the path to the RTK.
    def psyko(*cmd_args):
        env = os.environ
        env.pop("PLACE_CO_RUNNERS_LOCALLY", None)
        env["CORE_USED"] = f"{args.core}"
        if args.local_corunners:
            env["PLACE_CO_RUNNERS_LOCALLY"] = "1"

        cmd = [
            args.psyko,
            "-K", args.rtk_dir,
            "--product", args.product,
        ] + [*cmd_args]
        print("[RUN] ", end='')
        for item in cmd:
            print(f"'{item}' ", end='')
        print()

        # Run psyko... This is run in an infinite loop to handle timeouts...
        # This is especially annoying when you have a weak network connection and
        # that you fail to request a License. Since running all tests to collect
        # measures is quite slow, failing because of a timeout on such problems
        # is quite unpleasant.
        # So, in case of a network error (highly suggested by the timeout), we
        # just try again. It's kind of a kludge, but actually saved to much
        # time.
        def run_cmd(cmd):
            try:
                ret = subprocess.run(
                    cmd, timeout=30, cwd=TOP_DIR, env=env, universal_newlines=True)
                #print(cmd,TOP_DIR,env, sep='\n')
                assert ret.returncode == 0, "Failed to run psyko"
                return True
            except subprocess.TimeoutExpired:
                return False

        while not run_cmd(cmd):
            pass

    def psyko_cc(c_source):
        generated_object = object_of(c_source)
        psyko("cc", c_source, compile_config, "-o", generated_object)
        return generated_object

    def psyko_as(asm_source):
        generated_object = object_of(asm_source)
        psyko("as", asm_source, compile_config, "-o", generated_object)
        return generated_object

    def psyko_module(psy_source):
        generated_object = object_of(psy_source, ".psyo")
        psyko("module", psy_source, psymodule_config, "-o", generated_object)
        return generated_object

    def psyko_partition(name, objects):
        generated_object = args.build_dir / (name + ".parto")
        psyko("partition", "--gendir", "GEN", "-o", generated_object, *objects)
        return generated_object

    def psyko_app(partos, configs):
        elf = args.build_dir / "program.elf"
        psyko("app", "-a", args.build_dir / "program.app", "-b", args.output,
              '--gendir', args.build_dir / "gen" / "app",
              *partos, *configs)
        return elf

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
    # Finally, generate a single partition, and then the final executable
    parto = psyko_partition("main", parto_objects)
    psyko_app([parto], app_configs)
    assert args.output.is_file()

if __name__ == "__main__":
    main(sys.argv)
