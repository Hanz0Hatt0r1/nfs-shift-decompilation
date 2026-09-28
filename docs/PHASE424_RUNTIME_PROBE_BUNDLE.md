# Phase 424 — unified BMW M3 runtime-probe bundle

This phase composes the retail PE check, BMW M3 `aarm_multilink.sdf` domain check and runtime capture session validation into one fail-closed report.

Run:

`python tools/verify_bmw_m3_runtime_probe_bundle.py --shift SHIFT.zip --bff BMW_M3_E36.bff --pre pre_solve_XXXXXX.json --post post_solve_XXXXXX.json --frame frame_entry_XXXXXX.json -o bundle_report.json`

`--shift` accepts either `SHIFT.exe` or an archive containing exactly one `SHIFT.exe`. The bundle verifier does not synthesize a matrix/vector. Without `--pre` it stays blocked; without an expected session it reports structural readiness only. Supplying `--expected-session` enables exact numeric comparison through the existing cell/vector comparator.

The generated report exposes four independent gates: `retail_pe`, `bmw_m3_domain`, `frame_pre_post` and `numeric_expected`. A provider-backed frame is kept distinct from the builtin `FUN_007b0f20` path by the Phase 422 session consistency checks.
