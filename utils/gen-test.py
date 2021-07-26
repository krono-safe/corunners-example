#! /usr/bin/env python3
#
# Small utility used to generate the data structures of the stubs,
# that enables to cover all branches.

from random import randint  # <-- randint(a,b) -> [a,b] (inclusive)
import argparse
import sys


def gen_task_H():
    for i in range(512):
        print(f'''  [{i}] = {{
    .work_iterations = {randint(1,5)},
    .cond_h2_or_h5 = {randint(0,1)},
    .cond_h4_or_h9 = {randint(0,1)},
    .switch_value = {randint(0,2)},
  }},''')


def gen_task_G():
    for i in range(512):
        print(f'''  [{i}] = {{
    .work_iterations = {randint(3,7)},
    .cond_g14_or_g15 = {randint(0,1)},
    .switch_value = {randint(0,3)},
  }},''')


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('choice', choices=['task_H', 'task_G'])
    args = parser.parse_args(argv[1:])

    if args.choice == "task_H":
        gen_task_H()
    elif args.choice == "task_G":
        gen_task_G()


if __name__ == "__main__":
    main(sys.argv)
