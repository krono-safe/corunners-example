# This script contains functions to generate the code of co-runners:
# 1) JUMP co-runners, as a finite sequence of unconditional branches,
#   that eventually loops:
#
#   label_0: branch label_1
#   label_1: branch label_2
#   label_2: branch label_3
#   ...
#   label_n: branch label_0
#
# 2) READ co-runners, as a finite sequence of read and write in memory, that
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
# Both allow to generate code of a fixed size, without having to manually
# perform these changes.

LOOP_SIZE = 1024


def gen_header(symbol):
    return f"""
# This is a generated file")

  .global {symbol}
  .type {symbol}, @function

{symbol}:
  """


def gen_footer(symbol, suffix=""):
    return f"\tb {symbol}{suffix}\n\n \
            .size {symbol}, .- {symbol}"


def read_cor(symbol, tablesize=0x2000, startaddr="0x1380000", stride=4, nop=0):
    assert stride >= 0, "stride must be >= 0"
    assert tablesize >= 1, "tablesize must be >= 1"
    assert nop >= 0, "nop must be >= 0"

    result = gen_header(symbol)
    # Generate preamble
    result += "\tlis r3, global_data@ha\n"
    result += "\taddi r3,r3,global_data@l\n"
    #result += "\tdiab.li r0, 1337\n"
    result += f"\tlis r0, {startaddr}@ha\n"
    result += f"\taddi r0,r0,{startaddr}@l\n"
    result += f"{symbol}_loop:\n"

    for i in range(0, tablesize):
        result += f"\tlwz r4,{i*stride}(r0)\n"
        result += f"\tstw r4,0(r3)\n"
        for j in range(0, nop):
            result += "\tnop\n"

    result += gen_footer(symbol, suffix="_loop")
    result += f"""
\t.bss
\t.type global_data, @object
\t.size global_data,{stride}
\t.align 2
global_data:
\t.space {stride}
"""
    return result


def jump_cor(symbol, jumps=2048):
    assert jumps >= 1, "jumps must be >= 1"
    result = gen_header(symbol)
    for i in range(jumps - 1):
        result += f"\tb next{i}\nnext{i}:\n"
    result += gen_footer(symbol)
    return result
