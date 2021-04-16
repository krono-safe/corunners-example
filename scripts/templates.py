from os import environ as env
import __main__

assert __name__ != '__main__', f"{__file__} module cannot be run directly"

P2020 = env.get("P2020", "power-mpc5777m-evb")
MPC5777M = env.get("MPC5777M", "power-quoriq-ds-p")

CORES = [0, 1, 2]

TOP_DIR = __main__.Path(__main__.__file__).parent.resolve()
PSY_DIR = TOP_DIR / "psy"
SRC_DIR = TOP_DIR / "src"
CFG_DIR = TOP_DIR / "config"
STUBS_DIR = TOP_DIR / "psy" / "stubs"

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
    SRAM = "co_runner IDs stressing sram"
    MEM_CONF = "If set, this argument is a json file used to generate the memory placement"

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

LINK_CONFIG_HJSON_TEMPLATE = """
{
    link_options: {
      ldflags: [
        "-Xunused-sections-list"
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

CORUNNER_KMEMORY_JSON_TEMPLATE = """
{
  "domains": [
    {
      "output_sections": [
        {
          "name": ".text_${symbol}",
          "start_symbol": "_start__text_${symbol}",
          "end_symbol": "_end__text_${symbol}"
        }
      ],
      "protection": {
        "all_psyslayers": "EXECUTE"
      },
      "identifier": "${symbol}"
    },
    {
      "output_sections": [
        {
          "name": ".rodata_${symbol}",
          "start_symbol": "_start__rodata_${symbol}",
          "end_symbol": "_end__rodata_${symbol}",
          "type": "CONST"
        },
        {
          "name": ".data_${symbol}",
          "start_symbol": "_start__data_${symbol}",
          "end_symbol": "_end__data_${symbol}",
          "type": "DATA"
        },
        {
          "name": ".bss_${symbol}",
          "initialization": "CLEAR",
          "start_symbol": "_start__bss_${symbol}",
          "end_symbol": "_end__bss_${symbol}",
          "type": "BSS"
        },
        {
          "name": ".stack_${symbol}",
          "initialization": "CLEAR",
          "start_symbol": "_start__stack_${symbol}",
          "end_symbol": "_end__stack_${symbol}",
          "type": "BSS"
        }
      ],
      "protection": {
        "all_psyslayers": "READ_WRITE"
      },
      "identifier": "${symbol}"
    }
  ],
  "groups": [
    {
      "name": "${symbol}",
      "groups": [
        ".rodata_${symbol}",
        ".data_${symbol}",
        ".bss_${symbol}",
        ".text_${symbol}"
      ]
    },
    {
      "name": ".rodata_${symbol}",
      "sources": [
        ".rodata*"
      ],
      "destination": ".rodata_${symbol}"
    },
    {
      "name": ".data_${symbol}",
      "sources": [
        ".data*"
      ],
      "destination": ".data_${symbol}"
    },
    {
      "name": ".stack_${symbol}",
      "sources": [
        ".bss*",
        ".data*"
      ],
      "destination": ".stack_${symbol}"
    },
    {
      "name": ".bss_${symbol}",
      "sources": [
        ".bss*"
      ],
      "destination": ".bss_${symbol}"
    },
    {
      "name": ".text_${symbol}",
      "sources": [
        ".text*"
      ],
      "destination": ".text_${symbol}"
    }
  ],
  "objects": [
    {
      "id": "${symbol}",
      "type": "GLOBAL",
      "groups": [
        "${symbol}"
      ]
    }
  ]
}
"""
