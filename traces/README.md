# Traces

This directory contains the raw traces, collected from various executions on
the MPC5777M platform.

The naming of each files is explained as follows:

- the `c0-` or `c1-` prefix tells whether the core on which the task runs
  is the core 0 or the core 1;
- the `off` or `on` that follows indicates whether a co-runner is active on
  the other core (`on`) or not (`off`);
- the suffix `-local` indicates that co-runners (if enabled) are configured
  to only access core-local resources.


## Binary Format

The binary format is straightforward. It is a repeated sequence of:

- unsigned 16-bits: control node index that starts the EA;
- unsigned 16-bits: control node index that ends the EA;
- unsigned 32-bits: execution times of the EA, in timer ticks (the timer has a
  frequency of 5 MHz);
- unsigned 64-bits: earliest start date of the EA (logical time);
- unsigned 64-bits: deadline of the EA (logical time).
