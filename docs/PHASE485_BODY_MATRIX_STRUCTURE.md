# Phase 485 — BODY matrix structural builder

## Goal

Phase 485 reconstructs `FUN_007ba2b0`, the per-BODY contributor called by `FUN_007b2010` while building the pre-selection logical matrix.

## ABI

`void __thiscall FUN_007ba2b0(void *this,int param_1)`

`this` is the BODY runtime object and `param_1` is the logical matrix row-pointer table.

## BODY scalar groups

The BODY stores three structural group domains:

- width 3: count `+0x98`, storage `+0x160`, record stride `0x40`, scalar-index field `+0x30`;
- width 2: count `+0x9c`, storage `+0x164`, record stride `0xa0`, scalar-index field `+0x94`;
- width 1: count `+0xa0`, storage `+0x168`, record stride `0x60`, scalar-index field `+0x30`.

These storage arrays are allocated by `FUN_007ba4e0` with exactly `0x40`, `0xa0` and `0x60` bytes per record respectively.

## Matrix operation

For each source group and every target group, `FUN_007ba2b0` writes the Cartesian product of their scalar indices to the logical matrix.

Every selected cell receives exact binary64 `1.0`, and the transposed cell is written at the same time. Within-group products therefore include diagonal entries; cross-group products produce symmetric off-diagonal blocks.

The matrix was already fully zeroed by `FUN_007b2010` before this function runs.

## Structural interpretation

The per-BODY result is therefore a **union of symmetric support blocks**. Across all BODY calls, the global matrix support is the union of the block supports contributed by all bodies.

This is a strong upstream explanation for why the provider acceptance predicate can operate purely on zero/non-zero state.

## Remaining gap

The current phase does not reconstruct which concrete scalar indices populate each BODY group. Those indices are produced by earlier constraint/body staging functions. Once decoded, the block builder can be used to generate the full pre-acceptance sparsity mask directly and compare it with the recovered provider RLE signatures.

## Scope boundary

The `1.0` values are treated as structural support seeds, not final physical coefficients. No semantic variable names, units, or provider class identities are inferred.
