# Phase 397 — JOINT/HINGE projection equations

This phase hardens the `FUN_007bac60` / `FUN_007bae40` boundary without copying the earlier ambiguous destination-offset claims.

## JOINT — `FUN_007bac60`

The sample record stride is `0x40`, the side flag is at `+0x34`, and the scalar base index is at `+0x30`. Three cross-product terms are source-backed:

- `d2 = sample[+0x28]*body[+0x20] - sample[+0x20]*body[+0x28]`
- `d3 = body[+0x28]*sample[+0x18] - sample[+0x28]*body[+0x18]`
- `d5 = sample[+0x20]*body[+0x18] - body[+0x20]*sample[+0x18]`

The source then forms three scalar lanes `sign*d4`, `sign*d6`, `sign*d2`, where the side flag selects `+1` or `-1`. The direct function body is now available from the local full `SHIFT.exe.c` snapshot. `d4`, `d6` and `d7` are implemented below, and the destination is the per-body solver-vector contribution buffer at `this+0x150 + scalar_base*8`.

## HINGE — `FUN_007bae40`

The sample stride is `0xA0`, scalar base is `+0x94`, and side flag is `+0x98`. The zero-flag branch adds sample-frame velocity terms; the nonzero branch first transforms a sample-derived vector through `FUN_007aefb0(body +0xd4, ...)` and subtracts the transformed terms. The two scalar lane equations are now reconstructed exactly; their destination is `this+0x150 + scalar_base*8`.

The implementation exposes both boundaries as source-backed partial contracts rather than fabricating numerical formulas.
