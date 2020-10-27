#! /usr/bin/env python3

import argparse
from pathlib import Path
import sys

from scriptutil import get_nodes_to_ea, decode_file, gen_json_data, calc

C0_OFF = "Task: C0, Corunner: OFF"
C0_ON = "Task: C0, Corunner: ON"
C1_OFF = "Task: C1, Corunner: OFF"
C1_ON = "Task: C1, Corunner: ON"

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

SINGLE_EAS = {
    "G": ["G0"],
    "H": ["H0", "H1"],
}


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
    parser.add_argument("--c1-off", type=Path, required=True)
    parser.add_argument("--c1-on", type=Path, required=True)
    parser.add_argument("--output-dir", "-o", type=Path, required=True)
    parser.add_argument("--task", choices=["G", "H"], required=True)
    parser.add_argument("--stats", action='store_true')
    return parser.parse_args(argv[1:])


def gen_r_script(data, layout, single_eas, out_dir):
    rows, cols = check_layout(layout)

    script = f"""
library("rjson")
library("vioplot")

pdf(file="out.pdf")
par(mfrow=c({rows},{cols}), mar=c(3,3,1,1))
"""

    for row in layout:
        for ea in row:
            if ea is None:
                continue
            extra = ""
            if ea in single_eas:
                extra="wex=10,areaEqual = T,"
            minval = min(data[ea]["values"])
            maxval = max(data[ea]["values"])
            script += f"""
# For EA {ea} ##############################
result <- fromJSON(file = "{ea}.json")
data <- as.data.frame(result)

g1 <- data[ data$corunner == "OFF" , ]
g2 <- data[ data$corunner == "ON" , ]

vioplot(
    values~group,
    col="grey75", data=g1, plotCentre="line", side="left",
    ylim=c({minval}, {maxval}),
    xlab="{ea}", ylab="Time (ms)", {extra}
    line=2.1,
)
vioplot(
    values~group,
    col="grey50", data=g2, plotCentre="line", side="right", {extra}
    add=T
)

"""
    script += "dev.off()\n"
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "plot.R", "w") as stream:
        stream.write(script)


def gen_stats(data):
    text = r"""
\begin{tabular}{ |c|r|r|r||r|r|r| }\hline
   & \multicolumn{3}{c||}{\textbf{Core 1}} & \multicolumn{3}{c|}{\textbf{Core 2}} \\\hline
  \textbf{EA} & \textbf{max(a)} \textit{(ms)} & \textbf{max(b)} \textit{(ms)} & %
  $\bm{R(a, b)}$ \textit{(\%)}& %
  \textbf{max(c)} \textit{(ms)} & \textbf{max(b)} \textit{(ms)} & %
  $\bm{R(c, d)}$ \textit{(\%)} \\\hline
"""
    for ea, info in sorted(data.items()):
        values = {
            C0_OFF: 0.0,
            C0_ON: 0.0,
            C1_OFF: 0.0,
            C1_ON: 0.0,
        }


        for value, sample in zip(info["values"], info["sample"]):
            assert sample in values, f"Unknown sample {sample}"
            values[sample] = max(values[sample], value)

        r0 = calc(values[C0_OFF], values[C0_ON])
        r1 = calc(values[C0_OFF], values[C1_ON])
        text += f"${ea}$ & "
        text += f"{values[C0_OFF]:.4f} & {values[C0_ON]:.4f} & "
        if r0 > 10:
            text += r'\textbf{' + f"{r0:.4f} " + r'}'
        else:
            text += f"{r0:.4f}"
        text += ' & '
        text += f"{values[C1_OFF]:.4f} & {values[C1_ON]:.4f} &"
        if r1 > 10:
            text += r'\textbf{' + f"{r1:.4f} " + r'} '
        else:
            text += f"{r1:.4f}"
        text += ' \\\\\n'

    text += r"""\hline
\end{tabular}
"""
    print(text)



def main(argv):
    args = getopts(argv)

    # Map indexed by EA:
    #   (src,dst) => name
    ea_to_name, name_to_ea = get_nodes_to_ea(args)


    # The data received is a dictionnary indexed by SOURCE
    # and then by EA.
    # It contains a list of dictionaries where keys are:
    #   - measure (the value in ms)
    #   - esd: earliest start date in ms
    #   - ddl: deadline in ms
    #   - src: index of the control node that starts the ea
    #   - dst: index of the control node that closes:w the ea
    #
    # E.g.
    #
    # data = {
    #   "base": {
    #     (1,4): [
    #       {
    #         measure: 0.33
    #         esd: 32
    #         ddl: 33
    #         src: 1
    #         dst: 4
    #       }
    #     ]
    #   }
    # }
    #
    data = {
        C0_OFF: decode_file(args.c0_off),
        C0_ON: decode_file(args.c0_on),
        C1_OFF: decode_file(args.c1_off),
        C1_ON: decode_file(args.c1_on),
    }

    layout = LAYOUTS[args.task]
    single_eas = SINGLE_EAS[args.task]

    groups = {
        C0_OFF: ("Core 1", "OFF", False),
        C0_ON: ("Core 1", "ON", False),
        C1_OFF: ("Core 2", "OFF", False),
        C1_ON: ("Core 2", "ON", False),
    }
    jdata = gen_json_data(data, ea_to_name, args.output_dir, groups)
    gen_r_script(jdata, layout, single_eas, args.output_dir)

    if args.stats:
        gen_stats(jdata)

if __name__ == "__main__":
    main(sys.argv)
