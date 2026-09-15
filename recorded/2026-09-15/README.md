# Independent reproduction, 15 September 2026

A clean local clone at source revision `7258c78` ran `make test` with Python 3 and Verilator 5.050 on macOS ARM64. All seven runner tests passed. The exact nine-entry matrix passed its expected outcomes: three correct-design runs and six detected negative controls across three clock pairs.

`summary.json` records exact source hashes, verified upstream provenance, command lines, compiler and simulator durations, and result classification. Raw logs are retained here. Generated build products are omitted; the runner recreates them.

This is executed assertion checking under the documented finite stimulus. It does not establish a formal proof, analog metastability behaviour, or complete CDC sign off. Tool runtimes are not delivery estimates.
