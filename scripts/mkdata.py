#! /usr/bin/env python3

import argparse
from pathlib import Path
import json
import sys
import os
from string import Template

from scriptutil import get_nodes_to_ea, decode_file, gen_json_data, calc

P2020 = os.environ.get("P2020","power-qoriq-p2020-ds-p")
MPC5777M = os.environ.get("MPC5777M",  "power-mpc5777m-evb")

C0_OFF = "Task: C0, Corunner: OFF"
C0_ON = "Task: C0, Corunner: ON"
C1_OFF = "Task: C1, Corunner: OFF"
C1_ON = "Task: C1, Corunner: ON"

R_SCRIPT = str()

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
}

R_SCRIPT_HEADER_TEMPLATE = """
library(rjson)

# What follows is a combination of:
#  - https://www.r-graph-gallery.com/9-ordered-boxplot.html#grouped
#  - https://www.r-graph-gallery.com/96-boxplot-with-jitter.html

pdf(file="out.pdf")
par(mfrow=c(${rows},${cols}), mar=c(3,3,1,1))
"""

EA_R_TEMPLATE = """
# For EA ${ea} ##############################
result <- fromJSON(file = "${ea}.json")
data <- as.data.frame(result)

boxplot(
        values~sample,data=data,
        main=expression(${ea0}[${ea1_}] ~ "(n=${n})"),
        xaxt="n",
        cex.lab=1.2,
        col=gray.colors(2,rev=T,start=0.2,end=0.7,alpha=0.4),
        ylab="",
        xlab=""
)
title(ylab=expression("Time (ms)"), line=1.8, cex.lab=1.0)
axis(1,
     at = seq(1 , 5 , 1),
      labels = c('(a)','(b)','(c)','(d)','?'),
     tick=T , cex=0.3)
abline(v=${line}.5,lty=1, col="grey")

lvl <- levels(data$$sample)
props <- summary(data$$sample) / nrow(data)

for (i in 1:length(lvl)) {{
    l <- lvl[i]
    v <- data[ data$$sample==l, "values" ]
    j <- jitter(rep(i, length(v)), amount=props[i]/2)
    points(j, v, pch=20, col=rgb(0,0,0,0.7))
}}
"""

R_SCRIPT_FOOTER_TEMPLATE = """
# Total n: ${ns} (should be 1024)
dev.off()\n
"""


LATEX_HEADER_TEMPLATE = r"""
\begin{tabular}{ |c|r|r|r||r|r|r| }\hline
   & \multicolumn{3}{c||}{\textbf{Core ${core0}}} & \multicolumn{3}{c|}{\textbf{Core ${core1}}} \\\hline
  \textbf{EA} & \textbf{max(a)} \textit{(ms)} & \textbf{max(b)} \textit{(ms)} & %
  $$\bm{R(a, b)}$$ \textit{(\%)}& %
  \textbf{max(c)} \textit{(ms)} & \textbf{max(d)} \textit{(ms)} & %
  $$\bm{R(c, d)}$$ \textit{(\%)} \\\hline
"""

LATEX_FOOTER = r""" \\

\hline
\end{tabular}
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
    parser.add_argument("--c0-off", type=Path, required=True)
    parser.add_argument("--c0-on", type=Path, required=True)
    parser.add_argument("--c1-off", type=Path, required=False)
    parser.add_argument("--c1-on", type=Path, required=False)
    parser.add_argument("--output-dir", "-o", type=Path, required=True)
    parser.add_argument("--task", choices=["G", "H"], required=True)
    parser.add_argument("--stats", action='store_true')
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--symetric", '-s', action='store_true')
    parser.add_argument("--product", "-p", type=str, required=True,
                        choices=[P2020,MPC5777M])
    return parser.parse_args(argv[1:])


def gen_r_script(data, layout, out_dir, symetric):
    def complete_script(template, context):
        global R_SCRIPT
        R_SCRIPT += Template(template).substitute(context)

    rows, cols = check_layout(layout)
    complete_script(R_SCRIPT_HEADER_TEMPLATE, {"rows": rows,
                                               "cols": cols})
    ns = 0
    if symetric:
        sets = 4
    else:
        sets = 2

    for row in layout:
        for ea in row:
            if ea is None:
                continue
            minval = min(data[ea]["values"])
            maxval = max(data[ea]["values"])
            n = int(len(data[ea]["values"]) / sets)
            ns += n
            complete_script(EA_R_TEMPLATE, {"ea": ea,
                                            "ea0": ea[0],
                                            "ea1_": ea[1:],
                                            "n": n,
                                            "line": int(sets/2)})

    complete_script(R_SCRIPT_FOOTER_TEMPLATE, {"ns": ns})
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "plot.R", "w") as stream:
        stream.write(R_SCRIPT)


def gen_stats(data, symetric, cores, tex_name):
    text = Template(LATEX_HEADER_TEMPLATE).substitute({"core0": cores[0],
                                                       "core1": cores[1]})
    for ea, info in sorted(data.items()):
        values = {
            C0_OFF: 0.0,
            C0_ON: 0.0,
        }
        if symetric:
            values[C1_OFF] = 0.0
            values[C1_ON] = 0.0

        for value, sample in zip(info["values"], info["sample"]):
            assert sample in values, f"Unknown sample {sample}"
            values[sample] = max(values[sample], value)

        r0 = calc(values[C0_OFF], values[C0_ON])
        text += f"${ea}$ & "
        text += f"{values[C0_OFF]:.3f} & {values[C0_ON]:.3f} & "
        if r0 > 0.01:
            text += r'\textbf{' + f"{r0:.3f} " + r'}'
        else:
            text += f"{r0:.3f}"
        text += ' & '
        if symetric:
            r1 = calc(values[C1_OFF], values[C1_ON])
            text += f"{values[C1_OFF]:.3f} & {values[C1_ON]:.3f} &"
            if r1 > 0.01:
                text += r'\textbf{' + f"{r1:.3f} " + r'} '
            else:
                text += f"{r1:.3f}"
    text += LATEX_FOOTER
    print("To include the stats tex file add: '\input{", tex_name,"}' where you wants to include it", sep='')
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
    args = getopts(argv)

    # Map indexed by EA:
    #   (src,dst) => name
    ea_to_name, _ = get_nodes_to_ea(args)
    data = {
        C0_OFF: decode_file(args.c0_off),
        C0_ON: decode_file(args.c0_on),
    }

    if args.product == P2020:
        cores = [0, 1]
    else:
        cores = [1, 2]
    if args.symetric:
        data[C1_OFF] = decode_file(args.c1_off)
        data[C1_ON] =  decode_file(args.c1_on)

    layout = LAYOUTS[args.task]

    groups = {
        C0_OFF: (f"Core {cores[0]}", "OFF", False),
        C0_ON: (f"Core {cores[0]}", "ON", False),
    }

    if args.symetric:
        groups[C1_OFF] = ("Core {cores[1]}", "OFF", False)
        groups[C1_ON] = ("Core {cores[1]", "ON", False)

    jdata = gen_json_data(data, ea_to_name, args.output_dir, groups)
    gen_r_script(jdata, layout, args.output_dir, args.symetric)

    if args.stats:
        gen_stats(jdata, args.symetric, cores, args.output_dir.resolve() / f"stats_{args.task}")
    if args.output_json is not None:
        with open(args.output_json, "w") as outp:
            json.dump(jdata, outp, indent=2)


if __name__ == "__main__":
    main(sys.argv)
