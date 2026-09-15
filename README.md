# FIFO assertions you can execute

A FIFO can transfer data in a test and still have a broken local pointer or synchronizer pipeline. This example attaches SystemVerilog assertions to a small asynchronous FIFO without editing its RTL.

## Reproduce

Install Python 3, Verilator with `--binary`/`--timing` support, make, and a C++ compiler. On Ubuntu 24.04: `sudo apt-get install verilator g++ make python3`.

```sh
git clone https://github.com/Rivoryxa-Technologies/fifo-assertion-verification
cd fifo-assertion-verification
make test
```

Every run has a new `evidence/run-*` directory containing source hashes, generated variants, compiler logs, simulator logs, commands, durations, and a JSON summary. Compilation is bounded to 180 seconds and each simulation to 15 seconds. Compiler errors, missing tools, and timeouts cannot count as expected negative controls.

## Checks and exercised conditions

- Binary pointers advance exactly when the local request is accepted, and hold when full or empty blocks it.
- A source Gray pointer changes by no more than one bit at a local clock edge.
- Each synchronizer's second stage equals its first stage from the previous destination clock edge.
- The test fills and drains a four-entry, eight-bit FIFO four times, checks all 16 data words, and requires blocked writes, blocked reads, and four pointer wraps on each side.
- Three write/read half-period pairs run: 5/7, 7/5, and 4/11 ns. Clock periods are twice those values.

The unmodified design must pass all three runs. Two labelled temporary mutants each run at all three clock pairs: bypassing the write-pointer synchronizer stage must trigger `WRITE_SYNC_PIPELINE_FAILED`; advancing the write pointer while full must trigger `WRITE_POINTER_FAILED`. They are demonstrations of checker sensitivity, not discovered upstream defects. The original source stays unchanged.

## Scope and limits

These are bound SVA checks executed in digital simulation, not formal proofs or electrical CDC sign off. A synchronous simulator does not model analog metastability or physical timing constraints. Independent reset recovery, arbitrary FIFO depths/widths, every clock ratio, and all concurrent traffic sequences are outside this matrix. Reset is asserted on both sides at startup and released first on the write side, then on the read side while the FIFO is idle. This does not demonstrate reset recovery during traffic. Gray transitions are checked in their source domain; we do not incorrectly require a one-bit difference between destination samples, which can skip multiple source updates.

Exercise counters show that the stated events occurred. They are not complete functional/code coverage. The SVA `cover` statements are included for inspection; reported counts come from explicit counters required by the testbench.

## Source provenance

`rtl/async_fifo.sv` is copied byte for byte from [Rivoryxa-Technologies/cdc-verification](https://github.com/Rivoryxa-Technologies/cdc-verification) revision `72d8122a7c5d458afabff2f858fe76f134010009`, under its MIT licence retained here. See `UPSTREAM.json` for the exact hash. Assertions, runner, and testbench are original MIT-licensed demonstration code.

Tool runtimes are recorded per command and are not client delivery estimates. This is public demonstration material, not client RTL or production sign off.
