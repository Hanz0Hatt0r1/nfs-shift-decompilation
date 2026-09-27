# Phase 393 — Solver buffer export

`FUN_007ba570` is the direct bridge from the per-body SDF runtime object to the external solver buffers.

## Exact operation

The function iterates `+0xa4` primary entries at `+0x150` and adds them to `param_1`. It then iterates `+0xa8` secondary entries at `+0x154` and adds them to `param_2`. Each channel is an 8-byte double.

No scaling, matrix transform or sign inversion occurs in this function: it is a pure additive transfer.

This closes the explicit data path from SDF constraint projection through body accumulators into the buffers consumed by the next physics/solver stage.

The destination buffers remain caller-owned and are intentionally not assigned physical semantics.
