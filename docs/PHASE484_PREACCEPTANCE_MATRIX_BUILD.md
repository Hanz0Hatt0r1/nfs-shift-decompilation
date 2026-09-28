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

## Why this matters

This proves that acceptance is evaluating a freshly built logical matrix domain. It is not directly evaluating the provider's packed factor workspace, which is rebound only after a provider accepts.

This is the concrete storage-level explanation for the distinction made in Phases 454, 465 and 483.

## Scope boundary

The exact body/constraint contribution formulas inside `FUN_007ba2b0` remain a separate reconstruction target. This phase does not infer semantic matrix labels or physical meanings.
