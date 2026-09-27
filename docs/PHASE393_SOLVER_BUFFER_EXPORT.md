# Phase 393 — Solver buffer export

`FUN_007ba570` is the direct bridge from the per-body SDF runtime object to the global solver buffers.

## Exact operation

The function iterates `+0xa4` solver-vector contribution entries at `+0x150` and adds them to `param_1` (`PhysicsSystem +0x40`). It then iterates `+0xa8` solver-matrix contribution entries at `+0x154` and adds them to `param_2` (`PhysicsSystem +0x44`). Each channel is an 8-byte double.

No scaling, matrix transform or sign inversion occurs in this function: it is a pure additive transfer of solver vector/matrix contributions.

This closes the explicit data path from SDF constraint projection through per-body solver contributions into the global buffers consumed by the final physics/solver stage.

The destination buffers remain caller-owned and are intentionally not assigned physical semantics.
