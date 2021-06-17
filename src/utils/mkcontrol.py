#! /usr/bin/env python3

import argparse
from pathlib import Path
import sys
from scriptutil import get_nodes_to_ea, decode_file, gen_json_data, calc

C0_OFF = "Task: C0, Corunner: OFF"
C0_ON = "Task: C0, Corunner: ON"
C0_ON_LOCAL = "Task: C0, Corunner: ON (Local)"
C1_OFF = "Task: C1, Corunner: OFF"
C1_ON = "Task: C1, Corunner: ON"
C1_ON_LOCAL = "Task: C1, Corunner: ON (Local)"

def getopts(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--kdbv", type=Path, required=True)
    parser.add_argument("--kcfg", type=Path, required=True)
    parser.add_argument("--kapp", type=Path, required=True)
    parser.add_argument("--c0-off", type=Path, required=True)
    parser.add_argument("--c0-on", type=Path, required=True)
    parser.add_argument("--c0-on-local", type=Path, required=True)
    parser.add_argument("--c1-off", type=Path, required=True)
    parser.add_argument("--c1-on", type=Path, required=True)
    parser.add_argument("--c1-on-local", type=Path, required=True)
    parser.add_argument("--output-dir", "-o", type=Path, required=True)
    parser.add_argument("--task", choices=["FLASH"], required=True)
    parser.add_argument("--stats", action='store_true')
    return parser.parse_args(argv[1:])


def gen_r_script(data, out_dir):
    script = f"""
library("rjson")
library("vioplot")

pdf(file="out.pdf", width=8, height=4)
par(mfrow=c(2,2), mar=c(3,3,1,1))
"""

    for core in ["1", "2"]:
        for ea in ["F1", "F2"]:
            cval = int(core) - 1
            script += f"""
# For EA {ea} (core {core}) #########################
result <- fromJSON(file = "{ea}.json")
data <- as.data.frame(result)

g <- data[ data$group == "Core {core}" , ]
# n: number of samples per plot
t <- paste0("{ea} (core={core}, n=", dim(g)/3, ")")

m1 <- g$values[ g$sample=="Task: C{cval}, Corunner: OFF" ]
m2 <- g$values[ g$sample=="Task: C{cval}, Corunner: ON (Local)" ]
m3 <- g$values[ g$sample=="Task: C{cval}, Corunner: ON" ]

# I'm sorry for doing this... but the hardware target is so deterministic
# that sometimes I get measures for one EA that are systematically the same,
# so I end up with a big data frame with the same value that gets repeated.
# This does not go well with violplot...
# So, if all my values are identical, I add 1e-11 to my very first measure,
# so it can be taken as-is by vioplot to displpay a horizontal bar.
# Sorry, I'm too unfamiliar with R and such things...
# I don't think this is significant, though, as my measures are precise at
# 1e-7. So adding 1e^-11 JUST FOR THE DISPLAY should not harm in any way.
if (length(unique(m1)) == 1) {{ m1[1] <- m1[1] + 1e-11 }}
if (length(unique(m2)) == 1) {{ m2[1] <- m2[1] + 1e-11 }}
if (length(unique(m3)) == 1) {{ m3[1] <- m3[1] + 1e-11 }}

vioplot(
    m1,
    m2,
    m3,
    col="grey75", line=2.1,
    xlab=t, ylab="Time (ms)"
)
"""

    script += "dev.off()\n"
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "plot.R", "w") as stream:
        stream.write(script)


def gen_stats(data):
    table = [
        dict(),
        dict(),
    ]

    for ea, info in data.items():
        values = {
            C0_OFF: 0.0,
            C0_ON: 0.0,
            C0_ON_LOCAL: 0.0,
            C1_OFF: 0.0,
            C1_ON: 0.0,
            C1_ON_LOCAL: 0.0,
        }

        for value, sample in zip(info["values"], info["sample"]):
            assert sample in values, f"Unknown sample {sample}"
            values[sample] = max(values[sample], value)

        r0a = calc(values[C0_OFF], values[C0_ON_LOCAL])
        r0b = calc(values[C0_OFF], values[C0_ON])
        r1a = calc(values[C1_OFF], values[C1_ON_LOCAL])
        r1b = calc(values[C1_OFF], values[C1_ON])

        table[0][ea] = [
            values[C0_OFF],
            values[C0_ON_LOCAL],
            values[C0_ON],
            r0a,
            r0b,
        ]
        table[1][ea] = [
            values[C1_OFF],
            values[C1_ON_LOCAL],
            values[C1_ON],
            r1a,
            r1b,
        ]

    text = r"""
\begin{tabular}{ |c|c|r|r|r|r|r| }\hline
 & \textbf{EA} & \textbf{max(1)} \textit{(ms)} & \textbf{max(2)} \textit{(ms)} & \textbf{max(3)} \textit{(ms)} & %
  $\bm{R(1, 2)}$ \textit{(\%)}& %
  $\bm{R(1, 3)}$ \textit{(\%)} %
  \\\hline
"""

    for core, core_info in enumerate(table, 1):
        line = 0
        for ea, info in sorted(core_info.items()):
            if ea == "F0":
                continue
            if line == 0:
                text += r"\multirow{2}{*}{" + f"\\textbf{{Core {core}}}" + r'}'
                line += 1
            text += f' & {ea} & {info[0]:.3f} & {info[1]:.3f} & '
            text += f'{info[2]:.3f} & {info[3]:.3f} & {info[4]:.3f}'
            text += '\\\\'
            if line == 2:
                text += r'\hline'
            text += '\n'

    text += r"""\hline
\end{tabular}
"""
    print(text)

def main(argv):
    args = getopts(argv)

    # Map indexed by EA:
    #   (src,dst) => name
    ea_to_name, name_to_ea = get_nodes_to_ea(args)

    data = {
        C0_OFF: decode_file(args.c0_off),
        C0_ON: decode_file(args.c0_on),
        C0_ON_LOCAL: decode_file(args.c0_on_local),
        C1_OFF: decode_file(args.c1_off),
        C1_ON: decode_file(args.c1_on),
        C1_ON_LOCAL: decode_file(args.c1_on_local),
    }

    groups = {
        C0_OFF: ("Core 1", "OFF", False),
        C0_ON: ("Core 1", "ON", False),
        C0_ON_LOCAL: ("Core 1", "ON", True),
        C1_OFF: ("Core 2", "OFF", False),
        C1_ON: ("Core 2", "ON", False),
        C1_ON_LOCAL: ("Core 2", "ON", True),
    }

    jdata = gen_json_data(data, ea_to_name, args.output_dir, groups)
    gen_r_script(jdata, args.output_dir)
    if args.stats:
        gen_stats(jdata)

if __name__ == "__main__":
    main(sys.argv)
