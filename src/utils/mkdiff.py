#! /usr/bin/env python3

import argparse
from pathlib import Path
import json
import sys

from scriptutil import calc

C0_OFF = "Task: C0, Corunner: OFF"
C0_ON = "Task: C0, Corunner: ON"
C1_OFF = "Task: C1, Corunner: OFF"
C1_ON = "Task: C1, Corunner: ON"

def getopts(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("file1", type=Path)
    parser.add_argument("file2", type=Path)
    return parser.parse_args(argv[1:])



def gen_stats(data):
    text = r"""
\begin{tabular}{ |c|r|r|r||r|r|r| }\hline
   & \multicolumn{3}{c||}{\textbf{Core 1}} & \multicolumn{3}{c|}{\textbf{Core 2}} \\\hline
  \textbf{EA} & \textbf{max(a)} \textit{(ms)} & \textbf{max(b)} \textit{(ms)} & %
  $\bm{R(a, b)}$ \textit{(\%)}& %
  \textbf{max(c)} \textit{(ms)} & \textbf{max(d)} \textit{(ms)} & %
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
        r1 = calc(values[C1_OFF], values[C1_ON])
        text += f"${ea}$ & "
        text += f"{values[C0_OFF]:.3f} & {values[C0_ON]:.3f} & "
        if r0 > 0.01:
            text += r'\textbf{' + f"{r0:.3f} " + r'}'
        else:
            text += f"{r0:.3f}"
        text += ' & '
        text += f"{values[C1_OFF]:.3f} & {values[C1_ON]:.3f} &"
        if r1 > 0.01:
            text += r'\textbf{' + f"{r1:.3f} " + r'} '
        else:
            text += f"{r1:.3f}"
        text += ' \\\\\n'

    text += r"""\hline
\end{tabular}
"""
    print(text)



def main(argv):
    args = getopts(argv)

    with open(args.file1, "r") as inp:
        d1 = json.load(inp)
    with open(args.file2, "r") as inp:
        d2 = json.load(inp)

    def collect_values(info):
        values = {
            C0_OFF: 0.0,
            C0_ON: 0.0,
            C1_OFF: 0.0,
            C1_ON: 0.0,
        }
        for value, sample in zip(info["values"], info["sample"]):
            assert sample in values, f"Unknown sample {sample}"
            values[sample] = max(values[sample], value)
        return values

    text = r"""
\begin{tabular}{ |c|r|r|r||r|r|r| }\hline
   & \multicolumn{3}{c||}{\textbf{Core 1}} & \multicolumn{3}{c|}{\textbf{Core 2}} \\\hline
  \textbf{EA} & $\Delta_{max(a)}$ \textit{(ms)} & $\Delta_{max(b)}$ \textit{(ms)} & %
  $\Delta_{R(a, b)}$ \textit{(\%)}& %
  $\Delta_{max(c)}$ \textit{(ms)} & $\Delta_{max(d)}$ \textit{(ms)} & %
  $\Delta_{R(c, d)}$ \textit{(\%)} \\\hline
"""

    for ea in sorted(d1):
        info1 = d1[ea]
        info2 = d2[ea]
        vals1 = collect_values(info1)
        vals2 = collect_values(info2)

        r0_1 = calc(vals1[C0_OFF], vals1[C0_ON])
        r0_2 = calc(vals2[C0_OFF], vals2[C0_ON])
        r1_1 = calc(vals1[C1_OFF], vals1[C1_ON])
        r1_2 = calc(vals2[C1_OFF], vals2[C1_ON])
        text += f"${ea}$ & "
        text += f"{vals1[C0_OFF]-vals2[C0_OFF]:+.3f} & {vals1[C0_ON]-vals2[C0_ON]:+.3f} & "
        text += f"{r0_1-r0_2:+.3f} & "
        text += f"{vals1[C1_OFF]-vals2[C1_OFF]:+.3f} & {vals1[C1_ON]-vals2[C1_ON]:+.3f} & "
        text += f"{r1_1-r1_2:+.3f}"

        text += ' \\\\\n'

    text += r"""\hline
\end{tabular}
"""
    print(text)

if __name__ == "__main__":
    main(sys.argv)

