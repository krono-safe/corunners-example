# This file is imported by scripts around

import json
from collections import namedtuple
import tempfile
import struct
from subprocess import PIPE, run, TimeoutExpired, CalledProcessError
from string import Template
from sys import exit, stderr
from time import sleep
from io import IOBase

EA = namedtuple("EA", ["source", "target"])

def load_json(f, o=True):
    if ( isinstance(f, str) or isinstance(f, bytes) ) and not o:
        return json.loads(f)
    elif isinstance(f, IOBase):
        return json.load(f)
    else:
        with open(f, 'r') as jf:
            return json.load(jf)

def dump_json(obj, f=None, s=False):
    if s:
        return json.dumps(obj, indent=2)
    with open(f, 'w') as jf:
        json.dump(obj, jf, indent=2)

def substi_temp(template, context):
    return Template(template).substitute(context)

def write_template(output_filename, template, context):
    output_filename.parent.mkdir(exist_ok=True, parents=True)
    with open(output_filename, "w") as fileh:
        fileh.write(substi_temp(template, context))

def decode_file(input_file, timer):
    sorted_data = dict()

    # Data format is simple: 16-bits, 16-bits, 32-bits, 64-bits 64-bits
    # If the first two fields are zero, data stream is finished.
    data_format = ">2HI2Q"
    item_size = struct.calcsize(data_format)
    offset = 0
    count = 0
    all_time = 0
    with open(input_file, 'rb') as stream:
        contents = stream.read()

    while offset < len(contents):
        src, dst, val, esd, ddl = struct.unpack_from(data_format, contents, offset)
        offset += item_size
        count += 1

        # Val is the number of quota timer ticks.
        #   Time_s = NbTicks / Freq_Hz
        #
        # The ticker ticks at 5MHz for the MPC5777m and at 75MHz for the P2020.
        # We want a result in ms, so we * 1e3
        val_ms = float(val) / timer * 1e3
        all_time += val_ms

        # Esd/Ddl are in ns. Convert to us.
        esd = float(esd) / 1e3
        ddl = float(ddl) / 1e3

        ea = EA(source=src, target=dst)

        if not ea in sorted_data:
            print(f"=> {ea} ({src} -> {dst})")
            sorted_data[ea] = []
        sorted_data[ea].append({
            "measure": val_ms,
            "esd": esd,
            "ddl": ddl,
            "src": src,
            "dst": dst,
        })

    print(f"{count} measures processed, {len(contents)}, {input_file}")
    print(f"{all_time} ms of run-time, with quota timer of {timer:.1E}Mhz")
    return sorted_data


def load_db(kdbv, path_to_db):
    proc = run([kdbv, path_to_db], stdout=PIPE, check=True)
    return load_json(proc.stdout, o=False)


def get_nodes_to_ea(args):
    kcfg = load_db(args.kdbv, args.kcfg)
    kapp = load_db(args.kdbv, args.kapp)

    nodes_to_ea = dict()
    name_to_id = dict()

    cg = kcfg["control_graph"]
    for cg_node in cg["nodes"]:
        assert cg_node["type"] == "ADVANCE"
        name = cg_node["name"]
        name_to_id[name] = cg_node["global_index"]

    for ag in kapp["agents"]:
        if ag["name"] != f"task_{args.task}":
            continue
        for ea in ag["eas"]:
            src = name_to_id[ea["from"]]
            dst = name_to_id[ea["to"]]
            ea_tuple = EA(source=src, target=dst)
            nodes_to_ea[ea_tuple] = ea["name"]

    assert len(nodes_to_ea) != 0

    ea_to_nodes = dict()
    for key, val in nodes_to_ea.items():
        ea_to_nodes[val] = key
    return nodes_to_ea, ea_to_nodes


def gen_json_data(data, ea_to_name, out_dir, groups):
    # See the main function to understand how "data" is structured
    # In the end, the JSON data must look like this:
    #  {
    #    "EA0": {
    #      "values": [
    #        1,2,3,4,
    #        8,4,3,4,
    #        1,2,3,4,
    #        5,2,3,5
    #      ],
    #      "group": [
    #        "(A)", "(A)", "(A)", "(A)",
    #        "(A)", "(A)", "(A)", "(A)",
    #        "(B)", "(B)", "(B)", "(B)",
    #        "(B)", "(B)", "(B)", "(B)"
    #      ],
    #      "sample": [
    #        1,1,1,1,
    #        2,2,2,2,
    #        4,4,4,4,
    #        3,3,3,3
    #      ]
    #      "corunner": [
    #        OFF, OFF, OFF, OFF,
    #        ON, ON, ON, ON,
    #        OFF, OFF, OFF, OFF,
    #        ON, ON, ON, ON,
    #      ]
    #      "local": [
    #        True, True, True, True,
    #        True, True, True, True,
    #        True, True, True, True,
    #        False, False, False, False,
    #      ]
    #    }
    #    ...
    #  }

    jdata = dict()

    def process(sample, sample_data, group):
        for ea, ea_values in sample_data.items():
            ea_name = ea_to_name[ea]
            if not ea_name in jdata:
                jdata[ea_name] = {
                    "values": [],
                    "group": [],
                    "sample": [],
                    "corunner": [],
                    "local": [],
                }

            for value in ea_values:
                jdata[ea_name]["values"].append(value["measure"])
                jdata[ea_name]["sample"].append(sample)
                jdata[ea_name]["group"].append(group[0])
                jdata[ea_name]["corunner"].append(group[1])
                jdata[ea_name]["local"].append(group[2])

    for sample, sample_data in data.items():
        process(sample, sample_data, groups[sample])

    out_dir.mkdir(parents=True, exist_ok=True)
    for ea_name, ea_data in jdata.items():
        with open(out_dir / f"{ea_name}.json", "w") as stream:
            json.dump(ea_data, stream, indent=2)
    return jdata


# https://en.wikipedia.org/wiki/Relative_change_and_difference
def calc(ref, value):
    return (value - ref) / ref * 100.0

def psyko(conf, *cmd_args):
    cmd = [
        conf['psyko'],
        "-K", conf['rtk_dir'],
        "--product", conf['product'],
        '--color', 'yes',
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
            print(run( cmd, timeout=30, cwd=conf['cwd'], check=True,
              universal_newlines=True, stderr=PIPE).stderr, file=stderr)
            return True
        except TimeoutExpired:
            return False
        except CalledProcessError as e:
            err = e.stderr
            lmapi = 'Unknown LMAPI error' in err
            print(err, file=stderr)
            if lmapi:
              print('retrying in 60 seconds', file=stderr)
              sleep(60)
              return False
            else:
              exit("Failed to run psyko")

    while not run_cmd(cmd):
        pass
