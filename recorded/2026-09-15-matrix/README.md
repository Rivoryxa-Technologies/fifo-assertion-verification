# Recorded matrix evidence — 2026-09-15

Command, from the repository root:

```sh
python3 tools/run.py --evidence recorded/2026-09-15-matrix
```

Environment: `Verilator 5.050 2026-07-01 rev vUNKNOWN-built20260701`.

Result: `run-da36f9156cf7/summary.json` reports `ok: true` and verifies the pinned upstream source hash. All 12 parameterized builds completed without timeout. All 28 simulations were classified as expected: seven correct-source passes and 21 negative-control cases comprising 17 exact expected failures and four required non-triggering passes. The summary records commands, seeds, clock half-periods, phase offsets, hashes, durations, expected diagnostics, and per-case log paths.

The retained logs show the realistic selectivity of the full-boundary controls: `full_pointer` and `stale_full` pass both the short happy workload and the depth-8 read-faster workload, whose correct-source log records zero blocked writes. They fail only workloads that reach full. `sync_bypass` fails every workload with exactly its pipeline diagnostic.

This directory is immutable review evidence for the stated tool version and host run. Reproduction creates a new run ID rather than overwriting it.
