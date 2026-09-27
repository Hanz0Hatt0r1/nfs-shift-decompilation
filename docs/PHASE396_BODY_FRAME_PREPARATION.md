# Phase 396 — Body-frame preparation

`FUN_007ba7e0` is now reconstructed through two already-proven matrix primitives.

## Exact chain

1. `FUN_007af0a0(body + 0xd4, body + 0x18)` transforms the stored body vector into temporary local components.
2. Those components are multiplied by the float32 coefficients at `+0x128/+0x12c/+0x130`.
3. `FUN_007aefb0(body + 0xd4, scaled)` transforms the scaled vector through the transpose form of the same 3×3 basis.
4. The final vector is written to `+0x30/+0x38/+0x40`.

This is structurally `Mᵀ · diag(C) · M · v`, with float32 conversions at the retail boundaries.

No coordinate-system or physical-unit label is assigned to the resulting vector.
