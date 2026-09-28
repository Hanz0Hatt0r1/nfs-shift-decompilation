# Phase 467 — specialized-provider zero-baseline coverage

## Goal

Phase 467 reconstructs the cleanup/teardown baseline of the two specialized provider storage domains.

The retail cleanup helpers are:

- provider 0: `FUN_007d43c0`;
- provider 1: `FUN_007d5600`.

Both use direct zero assignments and `FUN_0040cec0(..., 0, size)` bulk clears.

## Provider 0 result

`FUN_007d43c0` contains 51 bulk-clear calls and 57 direct zero stores.

Inside the known solver regions this covers 370 of 1190 packed-workspace doubles (31.09%). The 40-double output vector is cleared completely.

## Provider 1 result

`FUN_007d5600` contains 34 bulk-clear calls and 24 direct zero stores.

Inside the known solver regions this covers 280 of 746 packed-workspace doubles (37.53%). The 34-double output vector is cleared completely.

## Interpretation

The cleanup functions do **not** zero the entire factor workspace. Therefore a solver pre-state cannot be reconstructed as a simple all-zero matrix. The remaining workspace state must come from other initialization/reset paths or from the caller's existing runtime state.

The output vectors, by contrast, have complete cleanup coverage in both providers.

Per-row coverage is retained in the runtime report so later phases can distinguish rows that are mostly cleared from rows that rely heavily on subsequent initialization.

## Scope boundary

Cleanup coverage proves only that a storage range is cleared by the specific cleanup function. It does not assign logical matrix semantics to the cleared slots, and it does not prove which upstream function populates the remaining workspace.

Run locally with:

    python specialized_provider_zero_baseline_runtime.py SHIFT.exe.c
