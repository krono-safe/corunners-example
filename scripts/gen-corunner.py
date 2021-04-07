#! /usr/bin/env python3
#
# This script generates the code of two types of co-runners:
# * FLASH co-runners, as a finite sequence of unconditional branches, that eventually loops:
#
#   label_0: branch label_1
#   label_1: branch label_2
#   label_2: branch label_3
#   ...
#   label_n: branch label_0
#
# Usage:
#   python3 gen-corunner.py --jumps 1024 > code.asm
#
# * SRAM co-runners, as a finite sequence of read and write in memory, that
# eventualy loops:
#
#   loop:
#   read read_register, read_addr
#   write read_register, write_addr
#   read read_register, (read_addr << 1*stride)
#   write read_register, (write_addr << 1*stride)
#   read read_register, (read_addr << 2*stride)
#   write read_register, (write_addr << 2*stride)
#   ...
#   read read_register, (read_addr << n*stride)
#   write read_register, (write_addr << n*stride)
#   branch loop
#
# nop intructions can be added between each sequence.
#
# Usage:
#   python3 gen-corunner.py --sram --startaddr "0x8000" \
#   --tablesize 1024 --stride 4 --nop 0 > code.asm
#
# Both enable to generate code of a fixed size, without having to manually
# perform these changes.


import argparse
import sys

parser = argparse.ArgumentParser()
parser.add_argument('symbol')
parser.add_argument('--sram', action='store_true')
parser.add_argument('--jumps', type=int, default=1)
parser.add_argument('--startaddr', type=str, default="0x1380000")
parser.add_argument('--tablesize', type=int, default=0x10000)
parser.add_argument('--stride', type=int, default=4)
parser.add_argument('--nop', type=int, default=0)
args = parser.parse_args(sys.argv[1:])
assert args.jumps >= 1, "--jumps must be >= 1"
assert args.stride >= 0, "--stride must be >= 0"
assert args.tablesize >= 1, "--tablesize must be >= 1"
assert args.nop >= 0, "--nop must be >= 0"

def gen_header():
  print(f"""
# This is a generated file")

  .global {args.symbol}
  .type {args.symbol}, @function

{args.symbol}:
  """)

def gen_footer(suffix=""):
  print(f"\tb {args.symbol}{suffix}\n")
  print(f".size {args.symbol}, .- {args.symbol}")

def sram_cor():
  # Generate preamble
  print("\tlis r3, global_data@ha")
  print("\taddi	r3,r3,global_data@l")
  #print("\tdiab.li r0, 1337")
  print(f"\tlis r0, {args.startaddr}@ha")
  print(f"\taddi	r0,r0,{args.startaddr}@l")
  print(f"{args.symbol}_loop:")

  for i in range(0, args.tablesize):
    print(f"\tlwz r4,{(i-1)*args.stride}(r0)")
    print(f"\tstw r4,{i*args.stride}(r3)")
    for j in range(0, args.nop):
      print("\tnop")

  gen_footer(suffix="_loop")
  print(f"""
\t.bss
\t.type global_data, @object
\t.size global_data,{args.tablesize*args.stride}
\t.align 2
global_data:
\t.space {args.tablesize*args.stride}
""")

def jump_cor():
  for i in range(args.jumps - 1):
    print(f"\tb next{i}\nnext{i}:")
  gen_footer()

gen_header()

if args.sram:
  sram_cor()
else:
  jump_cor()



