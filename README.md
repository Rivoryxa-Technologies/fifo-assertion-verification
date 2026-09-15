# FIFO assertions with concurrent data checking

This example binds SystemVerilog assertions to a small asynchronous FIFO and runs them beside an end-to-end data scoreboard. The upstream RTL remains byte-for-byte unchanged; the testbench drives independent producer and consumer clocks and checks every accepted read against the corresponding accepted write.

## Reproduce

Install Python 3, Verilator with `--binary`/`--timing` support, make, and a C++ compiler. On Ubuntu 24.04: `sudo apt-get install verilator g++ make python3`.

```sh
git clone https://github.com/Rivoryxa-Technologies/fifo-assertion-verification
cd fifo-assertion-verification
make test
```

Each run creates a new `evidence/run-*` directory containing hashes, generated mutant RTL, exact commands, compiler and simulator logs, durations, and `summary.json`. Builds are bounded to 180 seconds and simulations to 20 seconds. A timeout, missing tool, incomplete matrix, duplicate case, compilation error, wrong diagnostic, extra diagnostic, or pass banner accompanying a failure is rejected.

## Verification matrix

The runner compiles depths 4 and 8 at widths 5, 8, and 13 where used. Seven simulations per variant cover:

- an ordinary two-word happy path that neither fills nor wraps the depth-4/width-8 FIFO;
- full/empty blocking and four complete fill/drain rounds at depth 4/width 5 and depth 8/width 13;
- concurrent producer/consumer traffic at both depths and all three widths, including write-faster, read-faster, and unequal phase configurations;
- two independent deterministic PRNG streams and recorded seeds, so producer and consumer choices reproduce without depending on process scheduling.

The scoreboard records data on accepted write-clock edges and compares it on accepted read-clock edges. Concurrent cases transfer 65 words at depth 4 and 113 words at depth 8. Directed boundary cases require blocked writes, blocked reads, and at least four address-pointer wraps in both domains.

The original pointer, Gray-transition, blocked-request, and synchronizer-pipeline assertions remain active. Registered full and empty flags must also equal the preceding local-domain next-pointer comparison. These are local digital simulation properties: binary pointers advance only for accepted requests, source Gray pointers change by at most one bit per source edge, and synchronizer stage two equals the preceding destination-domain value of stage one.

## Targeted negative control

The runner generates one labelled temporary mutant; it does not edit `rtl/async_fifo.sv`. The mutant incorrectly advances the write pointer only when a write is requested while full **and** the data word is all ones. The ordinary happy path and all concurrent random cases reserve that value and therefore must pass for the mutant. Only the two directed full-boundary cases supply the trigger and must fail with exactly `WRITE_POINTER_FAILED`.

This split demonstrates a subtle temporal defect that escapes ordinary traffic while still proving the expected failing condition narrowly. It is an intentionally seeded checker-sensitivity test, not a claim about a defect found upstream.

## Scope and limits

This remains a toy, module-level simulation example. It is not a formal proof, SoC integration test, electrical CDC sign-off, metastability model, reset-recovery campaign, exhaustive clock-ratio sweep, or exhaustive parameter proof. Resets assert together at startup and release at different idle clock edges; reset interruption during traffic is untested. Depths other than 4 and 8, widths other than 5, 8, and 13, and traffic beyond the recorded seeds remain outside the matrix.

The data scoreboard and explicit exercise counters establish the events described above. They are not code or functional coverage metrics. Gray transitions are checked in the source domain; destination samples may legitimately skip source values.

## Source provenance

`rtl/async_fifo.sv` is copied byte for byte from [Rivoryxa-Technologies/cdc-verification](https://github.com/Rivoryxa-Technologies/cdc-verification) revision `72d8122a7c5d458afabff2f858fe76f134010009`, under its retained MIT licence. `UPSTREAM.json` pins the path and SHA-256. The runner refuses to execute if either revision metadata or the source hash changes. Assertions, runner, and testbench are original MIT-licensed demonstration code.

Tool runtimes are recorded per command and are not client delivery estimates. This repository is public demonstration material, not client RTL or production sign-off.
