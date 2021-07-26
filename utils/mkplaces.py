#! /usr/bin/env python3

import argparse
from pathlib import Path
import json
import sys
from os import environ
from copy import deepcopy
from sys import stderr

from scriptutil import get_nodes_to_ea, decode_file, gen_json_data, \
                       substi_temp, dump_json

P2020 = environ.get('P2020', 'power-qoriq-p2020-ds-p')
MPC5777M = environ.get('MPC5777M', 'power-mpc5777m-evb')
NVAL = int(environ.get('STUBBORN_MAX_MEASURES', '1024'))
NO_SEP = bool(environ.get('NO_SEP', ''))
IGN = environ.get('TRACE_IGN', '').split(':')

R_SCRIPT = str()
OF = 'out'

LAYOUTS = {
  "G": [
      ["G0",  "G1",  "G2",  "G3"],
      ["G4",  "G5",  "G6",  "G7"],
      ["G8",  "G9",  "G10", "G11"],
      ["G12", "G13", "G14", "G15"],
      ["G16", "G17", None,  None],
  ],
  "H": [
      ["H0",  "H1",  "H2",  "H3"],
      ["H4",  "H5",  "H6",  "H7"],
      ["H8",  "H9",  "H10", "H11"],
      ["H12", "H13", "H14", "H15"],
  ],
  'U': [['U0']]
}

R_SCRIPT_HEADER_TEMPLATE = """
library(rjson)
library("vioplot")

# What follows is a combination of:
#  - https://www.r-graph-gallery.com/9-ordered-boxplot.html#grouped
#  - https://www.r-graph-gallery.com/96-boxplot-with-jitter.html

pdf(file="${onefile}.pdf", 7.5*${sets}, 7.5*${sets})
par(mfrow=c(${rows},${cols}), mar=${sets}*c(3,3,1,1),
    oma=${sets}*c(0,0,1,0), lheight=${sets}, page=T)
par(xaxt="n")
"""

EA_R_TEMPLATE = """
# For EA ${ea} ##############################
result <- fromJSON(file = "${ea}.json")
data <- as.data.frame(result)
n <- ${n}
if(n == 1){
  plt <- plot
}else{
  plt <- vioplot
}
"""

TESTS_R_TEMPLATE = """
##For ${task} ###############################
p <- plt(values~sample, data=data,
    subset=grepl("${task}-", sample), drop=T,
    col=gray.colors(${sets},rev=T,start=0.4,end=0.8,alpha=1),
    #cex.axis=34,
    cex.axis=${sets}/3.1,
    las=2,
    lwd=${sets}/6,
    #side="left",
    plotCentre="line",
    pchMed=seq(0, ${sets},1),
    ann=F
)
#p
title(ylab="Time (ms)",
    line=1.2*${sets},
    cex.lab=2*${sets}/3,
)
pos <- "${pos}"
if(pos != ""){
  pos <- bquote(", pos="*.(pos))
}
axis(1, las = 2, at=seq(1, ${sets}, by=1), labels = F)
text(seq(1,${sets},by=1), par()$$usr[3] - 1.2,
     labels = as.vector(sort(unique(data$$sample))),
     srt=35, xpd=T, cex=${sets}/5, adj=1)
title(main=bquote(${ea0}[${ea1_}] ~ "(n="*.(n)*.(pos)*")"),
    cex.main=${sets},
)
abline(v=(seq(1, ${sets},1)), col="black", lty="dotted", lwd=${sets}/4)
"""

R_SCRIPT_FOOTER_TEMPLATE = """
dev.off()\n
"""


LATEX_HEADER_TEMPLATE = r"""
\begin{longtabu}{|c|${cols} }\hline
"""
LATEX_TASK_HEADER_TEMPLATE = r"""
   ${title} \\\hline
  \textbf{EA} ${subtitles} \\\hline%
"""

LATEX_FOOTER = r"""
\end{longtabu}
"""


def check_layout(layout):
    rows = len(layout)
    assert rows > 0
    cols = len(layout[0])
    for row in layout:
        assert len(row) == cols
    return rows, cols


def getopts(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--kdbv", type=Path, required=True)
    parser.add_argument("--kcfg", type=Path, required=True)
    parser.add_argument("--kapp", type=Path, required=True)
    parser.add_argument("--traces-dir", type=Path, required=True)
    parser.add_argument("--core", type=int, required=True)
    parser.add_argument("--corunner-core", type=int)
    parser.add_argument("--output-dir", "-o", type=Path, required=True)
    parser.add_argument("--task", choices=["G", "H", 'U'], required=True)
    parser.add_argument("--timer", type=float, required=True)
    parser.add_argument("--stats", action='store_true')
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--product", "-p", type=str, required=True,
                        choices=[P2020, MPC5777M])

    return parser.parse_args(argv[1:])


def gen_r_script(data, layout, sets, out_dir):
    def complete_script(template, context):
        global R_SCRIPT
        R_SCRIPT += substi_temp(template, context)

    def complete_test(ea, sets, task):
        complete_script(TESTS_R_TEMPLATE, {
                                            'ea0': ea[0],
                                            'ea1_': ea[1:],
                                            'sets': sets,
                                            'pos': task[1:],
                                            'task': task
                                           })

    rows, cols = check_layout(layout)
    ns = 0
    m = 0
    info_set = sorted(set(list(data.values())[0]['sample']))
    tests = {}
    ntests = len(info_set)

    for sample in info_set:
        t, c = sample.split('-')
        if t not in tests.keys():
            tests[t] = list()
        tests[t].append(c)
        if not NO_SEP:
            length = len(tests[t])
            if length > m:
                m = length
    if NO_SEP:
        m = sets

    complete_script(R_SCRIPT_HEADER_TEMPLATE, {'rows': 1,
                                               'cols': 1,
                                               'sets': m,
                                               'onefile': OF})

    for ea in [g for r in layout for g in r if g]:
        n = int(len(data[ea]["values"]) / sets)
        ns += n
        complete_script(EA_R_TEMPLATE, {'ea': ea,
                                        'n': n})
        if not NO_SEP:
            for task in tests.keys():
                complete_test(ea, len(tests[task]), task)
        else:
            complete_test(ea, sets, "")
            complete_test

    complete_script(R_SCRIPT_FOOTER_TEMPLATE, {"ns": ns,
                                               "nt": NVAL})
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "plot.R", "w") as stream:
        stream.write(R_SCRIPT)


def gen_stats_header(d):
    cols = 0
    for k, v in d.items():
        subtitles = ''
        leng = len(v[0])
        cols = max(cols, leng)
        title = f"&\\multicolumn{{{leng}}}{{c|}}{{\\textbf{{{k[0]} {k[1:]}}}}}"
        for j in v[0]:
            s = f"& \\textbf{{max({j})}} \\textit{{(ms)}}"
            if j == 'COFF':
                subtitles = s + subtitles
            else:
                subtitles += s
        v[1] = substi_temp(LATEX_TASK_HEADER_TEMPLATE, {
                                                        'title': title,
                                                        'subtitles': subtitles
                                                       })

    return cols


def gen_stats(data, layout, tex_name):
    info_set = sorted(set(list(data.values())[0]['sample']))
    bvalues = {}
    tests = {}
    ntests = len(info_set)

    for sample in info_set:
        t, c = sample.split('-')
        if t not in tests.keys():
            tests[t] = [list(), '']
        tests[t][0].append(c)
        bvalues[sample] = 0.0
    cols = gen_stats_header(tests)
    text = substi_temp(LATEX_HEADER_TEMPLATE, {'cols': 'X|'*cols})

    for ea in [g for r in layout for g in r if g]:
        info = data[ea]
        values = deepcopy(bvalues)
        for value, sample in zip(info["values"], info["sample"]):
            assert sample in values, f"Unknown sample {sample}"
            values[sample] = max(values[sample], value)
        for k, v in tests.items():
            s = ''
            for c in v[0]:
                tmps = f"& {values[k+'-'+c]:.3f}"
                if c == 'COFF':
                    s = tmps + s
                else:
                    s += tmps
            s = f"${ea}$" + s

        v[1] += f"\n{s}\\\\"
    for v in tests.values():
        text += f"{v[1]}\\hline"
    text += LATEX_FOOTER
    print(r"To include the stats tex file add: '\input{", tex_name,
          "}' where you wants to include it \
           (requires to use the tabu and longtables packages)",
          sep='', file=stderr)
    with open(tex_name.with_suffix('.tex'), "w") as stream:
        stream.write(text)


def main(argv):
    """
    The data received is a dictionnary indexed by SOURCE and then by EA.
    It contains a list of dictionaries where keys are:
      - measure (the value in ms)
      - esd: earliest start date in ms
      - ddl: deadline in ms
      - src: index of the control node that starts the ea
      - dst: index of the control node that closes:w the ea

    E.g.
      data = {
        "base": {
          (1,4): [
            {
              measure: 0.33
              esd: 32
              ddl: 33
              src: 1
              dst: 4
            }
          ]
        }
      }
    """
    if IGN and IGN != ['']:
        global OF
        OF += '_zoomed'
    args = getopts(argv)
    if args.corunner_core is None:
        args.corunner_core = abs(1-args.core)
    cores = [args.core, args.corunner_core]

    # Map indexed by EA:
    #   (src,dst) => name
    ea_to_name, _ = get_nodes_to_ea(args)

    data = {}
    groups = {}
    print(IGN)
    for f in args.traces_dir.iterdir():
        if f.suffix == '.bin':
            name = str(f.stem).upper()
            if name not in IGN:
                print(name)
                data[name] = decode_file(f, args.timer)
                groups[name] = (f"Core {cores[0]}", "ON", False)
    layout = LAYOUTS[args.task]

    jdata = gen_json_data(data, ea_to_name, args.output_dir, groups)
    gen_r_script(jdata, layout, len(data), args.output_dir)

    if args.stats:
        pass
        #gen_stats(jdata, layout, args.output_dir.resolve() /
        #          f"stats_{args.task}")
    if args.output_json is not None:
        with open(args.output_json, "w") as outp:
            dump_json(jdata, outp)


if __name__ == "__main__":
    main(sys.argv)
