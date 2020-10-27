# Co-Runners Example

| :warning: **This repository relies on an experimental version of ASTERIOS for research projects.** |
| --- |

| :warning: **It does not necessarily reflect the current state of the industrial product.**         |
| --- |


This repository contains the PsyC sources showcasing how co-runners can help in
the characterization of timing anomalies caused by simultaneous accesses to
shared hardware resources.

## Pre-requisites

- [ASTERIOS][1] **Research**, with **experimental** support for co-runners
  on the MPC5777M platform.
  There is currently no trial version, but feel free to contact us to
  discuss **academic use**.
- [Python 3.6][2] or greater.
- The [R language][3], with additional libraries:
  - [rjson][4]; and
  - [vioplot][5].
- Only tested on a GNU/Linux distribution.


## Build an application

The `build.py` script enables to build the sources that reside in this
repository, with different co-runners and different memory positioning
schemes.
Some examples are provided below. `<psyko>` an `<rtk_dir>` refer to
paths to the PsyC compiler and to the ASTERIOS RTK directory.
For details, please run:

```
./build.py --help
```

This results in artifacts produced by default in the `build/` directory.
Unless specified otherwise, the final executable, ready to be flashed on
a hardware target will reside at path `build/program.elf`.

## Flashing an application

Use the [Trace32][6] scripts provided by the ASTERIOS RTK to flash the
generated application. Please refer to the ASTERIOS RTK manual for details.


## Execution of an application

Once the application has been flashed on the hardware, place a breakpoint
on the functions `k2_init()` and `em_raise()`. `k2_init` should be reached
without much delay after startup. Then run the target, and wait for `em_raise`
to be hit.
This function will be automatically called when all measures have been taken.
Then, run the target. It may take a while before this process completes.

When `em_raise()` has been reached, make sure that the value of the parameter
`error_id` matches the numerical value of `ERROR_STUBBORN_BUFFER_FULL` (see the
ASTERIOS RTK manual). A different value means an unexpected error has been
encountered.

Then, use Trace32 to dump to your filesystem the contents of the buffer
at the address of the symbol `k2_stubborn_measures`. It has a size of
`0x6000` bytes.


## Full reproducibility

The shell script [`scripts/run.sh`](scripts/run.sh) can be used to fully
reproduce the documents (figures and tables) used in the original paper. Note
that it has only be tested on a GNU/Linux system.
Run:

```
./scripts/run.sh \
  -p <path/to/psyko> \
  -k <path/to/RTK> \
  -d <path/to/kdbv> \
  -t <hook> \
  -T <type>
```

with:

- `<path/to/psyko>`, `<path/to/RTK>` and `<path/to/kdbv>` being paths to
  ASTERIOS-specific software.
- `<hook>` is the path to an executable file (e.g. shell script) that shall
  drive the execution of Trace32. It is systematically called after an
  application has been compiled, to run and retrieve measures. More details are
  provided in the next section.
- `<type>` can be one of:
  - `H`: to build the task `H`;
  - `G`: to build the task `G`;
  - `flash`: to build the task `flash`.

When the script completes, instructions are printed on the standard output
to explain how to generate the resources.

### The Hook

The hook is not provided in the open-source repository, because it contains
parts of the Trace32 software, we cannot distribute. It takes the following
parameters:

- the path to the compiled application, to be flashed;
- the core on which the compiled task must run;
- the path to the file that shall contain the resulting measures.

It should typically perform the following operations:

1. generate a CMM script with the input parameters, to provide Trace32
   directives on how to flash the application;
2. drive the execution of Trace32 to flash and run the application and retrieve
   measures. `trunner` (see next section) can help you doing exactly that.

### Compiling trunner

[`t32/main.c`](t32/main.c) is a small C source file (for POSIX-compliant
systems, e.g. Linux) that must be compiled with the C API provided by Trace32.
It contains the execution logic required to automatize execution and measures
retrieval.
You can generate an object file from this source by running:

```
gcc -std=gnu11 -Wall -Wextra -c -o main.o t32/main.c
```

You then must link this object file against the C library provided by Trace32 to
generate the `trunner` executable. It takes two arguments:

1. the path to the CMM script;
2. the path to the output file in which the measures will be dumped.



## License

This repository is under the [Apache-V2 license](LICENSE.md).


[1]: http://www.krono-safe.com/
[2]: https://www.python.org/downloads/release/python-360/
[3]: https://www.r-project.org/
[4]: https://cran.r-project.org/web/packages/rjson/index.html
[5]: https://cran.r-project.org/web/packages/vioplot/index.html
[6]: https://www.lauterbach.com
