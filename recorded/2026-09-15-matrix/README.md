# Recorded matrix evidence — 2026-09-15

Command, from the repository root:

```sh
python3 tools/run.py --evidence recorded/2026-09-15-matrix
```

Environment: `Verilator 5.050 2026-07-01 rev vUNKNOWN-built20260701`.

Result: `run-af19139e04e7/summary.json` reports `ok: true` and verifies the pinned upstream source hash. All six parameterized builds completed without timeout. All 14 simulations were classified as expected: seven correct-source passes, five non-triggering mutant passes, and two boundary-only mutant failures containing exactly `WRITE_POINTER_FAILED`. The summary records exact commands, seeds, clock half-periods, phase offsets, hashes, durations, and per-case log paths.

This directory is immutable review evidence for the stated tool version and host run. Reproduction creates a new run ID rather than overwriting it.
