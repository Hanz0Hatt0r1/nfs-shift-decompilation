# Phase 395 — Body-state primitives

Two low-level body-state operations are now source-backed.

## Coefficient initialization — `FUN_007ba860`

The function stores three float32 input coefficients at `+0x128/+0x12c/+0x130` and writes their double reciprocals at `+0x138/+0x140/+0x148`, then enters `FUN_007ba7e0`.

## Point contribution — `FUN_007ba9e0`

Given world point `p`, body origin `o` and contribution `v`, the function first derives `r = p - o`. It adds `v` to linear accumulator `+0x60/+0x68/+0x70` and `r×v` to angular accumulator `+0x48/+0x50/+0x58`.

This primitive is structurally related to `FUN_007baa70/baaf0`, but the lever arm is derived from the world point instead of supplied directly.

No physical units are inferred from either operation.
