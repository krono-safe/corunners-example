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

BUFSIZE=128
parser = argparse.ArgumentParser()
parser.add_argument("symbol")
parser.add_argument('--sram', action='store_true')
parser.add_argument("--jumps", type=int, default=1)
args = parser.parse_args(sys.argv[1:])
assert args.jumps >= 1, "--jumps must be >= 1"

print(f"""
# This is a generated file")

.global {args.symbol}
.type {args.symbol}, @function

""")

# Generate preamble
if args.sram:
    print(f"{args.symbol}:")
    print("\tlis r3, global_data@ha")
    print("\te_add16i	r3,r3,global_data@l")
    print("\tdiab.li r0, 1337")
    print(f"{args.symbol}_loop:")
else:
    print(f"{args.symbol}:")


for i in range(args.jumps - 1):
    print(f"\tb next{i}\nnext{i}:")

if args.sram:
    for i in range(0, BUFSIZE):
        print(f"\tstw r0,{i*4}(r3)")
    print(f"\tb {args.symbol}_loop\n")
else:
    print(f"\tb {args.symbol}\n")

print(f".size {args.symbol}, .- {args.symbol}")

if args.sram:
    print(f"""
\t.bss
\t.type global_data, @object
\t.size global_data,{BUFSIZE*4}
\t.align 2
global_data:
\t.space {BUFSIZE*4}
""")
