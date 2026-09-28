# Phase 414 — BMW M3 solver capture CLI

Phase 414 adds a one-command orchestration layer between the real BMW M3 resource and the solver-capture verifier.

The command validates the supplied `BMW_M3_E36.bff` against the exact archive/resource hashes already recorded by Phase 405, loads a normalized solver capture JSON, and performs the Phase 413 BMW structural check.

With `--expected-capture`, it additionally runs the Phase 411 exact RHS/matrix/storage comparison with caller-selected absolute and relative tolerances.

Without `--expected-capture`, the result is deliberately `verified-structure`: no solver values are invented.

Example:

```bash
python tools/verify_bmw_m3_solver_capture.py BMW_M3_E36.bff solver_capture.json
```

Exact numeric comparison:

```bash
python tools/verify_bmw_m3_solver_capture.py BMW_M3_E36.bff observed.json \
  --expected-capture expected.json \
  --abs-tol 1e-9 \
  --rel-tol 1e-9 \
  -o report.json
```

The CLI does not fabricate or bundle proprietary capture data.