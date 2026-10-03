# Phase 484 — pre-acceptance logical matrix construction

## Goal

Phase 484 reconstructs the portion of `FUN_007b3820` that builds the logical solver matrix before any provider acceptance check.

## Exact construction

1. `FUN_007b1b60(param_1)` computes the scalar count and writes it to `physics_system+0x34`.
2. `FUN_00638340(scalar_count * scalar_count * 8, 7)` allocates the matrix pool at `physics_system+0x38`.
3. `FUN_008868d0(scalar_count * 4, ...)` allocates the row-pointer table at `physics_system+0x3c`.
4. Each pointer is written as:

`row_pointer[row] = matrix_base + scalar_count * row * 8`

5. `FUN_007b2010(physics_system, row_pointer_table, scalar_count)` runs before provider acceptance.
6. Inside `FUN_007b2010`, every matrix double is zeroed and `FUN_007ba2b0(body, row_pointer_table)` is called once per BODY.
7. The resulting row-pointer table is passed to provider vtable `+0x14` acceptance.

## Independent memory-wrapper cross-check

The runtime contract can optionally consume
`SHIFT-MEMORY-SOURCE-SEMANTIC-SUMMARY/1`. For this Phase 484 path the
cross-check is considered ready only when:

- the summary contains the `FUN_008868d0` wrapper profile;
- `allocation-size` is a proven source role;
- the role has one stable source argument index;
- that index is `0`, matching the first argument in
  `FUN_008868d0(scalar_count * 4, ...)`;
- the proven caller inventory includes `FUN_007b3820`.

When all conditions hold, the contract status becomes
`source-and-diagnostic-backed-preacceptance-matrix-build` and records the
cross-check under `memory_wrapper_evidence`.

This does **not** rename or infer the remaining `FUN_008868d0` parameter, prove
the complete allocator ABI, identify a pool selector, or prove that every
allocation in the wrapper family has the same higher-level purpose. The original
source-backed Phase 484 contract remains valid independently of this optional
cross-check.

## Why this matters

This proves that acceptance is evaluating a freshly built logical matrix domain. It is not directly evaluating the provider's packed factor workspace, which is rebound only after a provider accepts.

This is the concrete storage-level explanation for the distinction made in Phases 454, 465 and 483.

## Scope boundary

The exact body/constraint contribution formulas inside `FUN_007ba2b0` remain a separate reconstruction target. This phase does not infer semantic matrix labels or physical meanings.
