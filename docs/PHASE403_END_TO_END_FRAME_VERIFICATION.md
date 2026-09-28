# Phase 403 — End-to-end solver-frame verification

This phase adds a strict structural verifier around the existing unified SDF frame contract.

## Checks

The verifier requires the exact eight-stage lifecycle from `FUN_007b3f40` through `FUN_007b4110`. It validates scalar-domain coverage, rejects overlapping/gapped scalar ranges, confirms identity-reset nodes stay inside the solver domain, and checks the six named frame stages in the runtime plan.

The verifier is intentionally structural. It does not claim provider numerical equivalence and does not replace `FUN_007b0f20`.

`sdf_full_frame_runtime.build_runtime_frame_plan()` now returns the verification result and the scalar-domain verification result alongside the existing identity-selection plan.
