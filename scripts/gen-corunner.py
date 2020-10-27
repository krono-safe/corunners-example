#! /usr/bin/env python3
#
# This script generates the code of FLASH co-runners, as a finite sequence
# of unconditional branches, that eventually loops:
#
#   label_0: branch label_1
#   label_1: branch label_2
#   label_2: branch label_3
#   ...
#   label_n: branch label_0
#
# It enables to generate code of a fixed size, without having to manually
# perform these changes.
#
# Usage:
#   python3 gen-corunner.py --jumps 1024 > code.asm
#

import argparse
import sys

parser = argparse.ArgumentParser()
parser.add_argument("symbol")
parser.add_argument("--jumps", type=int, default=1)
args = parser.parse_args(sys.argv[1:])
assert args.jumps >= 1, "--jumps must be >= 1"

print(f"""# This is a generated file
.global {args.symbol}
.type {args.symbol}, @function

{args.symbol}:
""")

for i in range(args.jumps - 1):
    print(f"\tb next{i}\nnext{i}:")

print(f"\tb {args.symbol}\n")
print(f".size {args.symbol}, .- {args.symbol}")
