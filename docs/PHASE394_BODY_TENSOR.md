# Phase 394 — Body tensor preparation

`FUN_007ba630` builds the body-side symmetric 3×3 tensor consumed by the later frame projection code.

## Source inputs

Three diagonal coefficients are stored at `+0x138`, `+0x140` and `+0x148`. The 3×3 basis is stored as float32 values at `+0xd4..+0xf4` in three source rows.

## Exact operation

The source computes `B * diag(D) * Bᵀ`. Output storage is symmetric at `+0xb0/+0xb4/+0xb8`, `+0xbc/+0xc0/+0xc4`, `+0xc8/+0xcc/+0xd0`.

The duplicate stores are explicit: `+0xbc` mirrors `+0xb4`, `+0xc8` mirrors `+0xb8`, and `+0xcc` mirrors `+0xc4`.

`FUN_007ba860` provides the related initialization boundary by computing reciprocal diagonal values from `+0x128/+0x12c/+0x130` into `+0x138/+0x140/+0x148` before frame preparation.

The implementation mirrors retail float32 consumption and deliberately leaves the tensor's physical interpretation unnamed.
