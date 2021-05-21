# Traces

This directory contains the raw traces, collected from various executions on
the MPC5777M and the P2020 platform.

For the `G`, `H`, `U`, `flash` and `flash2` tests, the naming of each files is explained as follows:

- the `c0-` or `c1-` prefix tells whether the core on which the task runs
  is the core 1 or the core 2 (yes, there is an offset here...);
- the `off` or `on` that follows indicates whether a co-runner is active on
  the other core (`on`) or not (`off`);
- the suffix `-local` indicates that co-runners (if enabled) are configured
  to only access core-local resources.

This terminology is a bit different for `Hsram` (only for the MPC5777m): when `on`  is present,
a SRAM-stressing co-running is active on core 0.

For the `places` tests, the naming of each file is explained as follows:
  - the first letter is the task used to perform the test;
  - the number is the placement of the task. The decimal separator must be put after the first digit to have the placement value in GB;
  - for the second part of the file name, it represents the corunner placement. It is formed the same way as the task string (except that the first letter never changes).
  - The corunner may also be marked `OFF` if there is no corunner.

For the `cpupri` test, the naming of each file is explained as follows:
  - the first part represents the priority of the first core;
  - the second part represents the priority of the second core.
  - the different priorities are:
    * `low` for lowest priority;
    * `sec` for second lowest priority;
    * `high` for highest priority;
    * `res` for reserved (to test if the reserved value does not work, if the result is unpredictable or if it is constant).
  - the ref-coff test if a reference test withwout corunners and with the default priority (low-low).

For the `Hsram` test (only for the P2020), the naming of each file is explained as follows:
  - the first letter is the task used to perform the test;
  - the rest of the first part represents the placement of the task;
  - for the first half of the second part of the file name, it represents the corunner placement. It is formed the same way as the task string (except that the first letter never changes).
  - the second half of the second part, folowing the `_` symbol, is the region the corunner reads from.
  - the different places are:
    * `DDR` for the DDR;
    * `SRAM` for the L2SRAM not partitionned;
    * `R1` for the first region of the L2SRAM partitionned in two halves;
    * `R2` for the second region region of the L2SRAM partitionned in two halves.
  - The corunner may also be marked `OFF` if there is no corunner.

For the `l1` test, the meaning of each file is explained as follows:
  - the first part represents the task;
  - For the second part of the file name, it represents the corunner. It is formed the same way as the task string (except that the first letter never changes).
  - the second half of each part represents activated l1 caches:
    * `I` for the instructtion cache;
    * `D` for the data cache.
  - if a cache is nor present in the name, it is desactiated;
  - The corunner may also be marked `OFF` if there is no corunner.


## Binary Format

The binary format is straightforward. It is a repeated sequence of:

- unsigned 16-bits: control node index that starts the EA;
- unsigned 16-bits: control node index that ends the EA;
- unsigned 32-bits: execution times of the EA, in timer ticks (the timer has a
  frequency of 5 MHz);
- unsigned 64-bits: earliest start date of the EA (logical time);
- unsigned 64-bits: deadline of the EA (logical time).


## JSON Format

Measures in textual JSON format are present for task H with and without the
SRAM co-runner scenario. These are a dump of processed binary data, that can be
taken as an input by `scripts/mkdiff.py`.
