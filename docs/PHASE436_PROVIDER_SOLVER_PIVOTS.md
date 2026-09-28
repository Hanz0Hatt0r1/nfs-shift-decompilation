# Phase 436 — specialized-provider pivot geometry

Phase 436 uses the local retail SHIFT.exe.c source to close the pivot-layout
boundary of FUN_007c7200 and FUN_007cdfc0.

## Provider 0

FUN_007c7200 contains exactly 40 unique reciprocal pivot denominators across
the 40-scalar provider domain. The first reciprocal is at source line 825794
and the final unique pivot reciprocal is at 827122.

For every scalar index i:

    pivot_diagonal_address = row_pointer[i] + 8*i

The first three pivots are:

    i=0 -> 0x00C21738
    i=1 -> 0x00C21808
    i=2 -> 0x00C218D8

## Provider 1

FUN_007cdfc0 contains exactly 34 unique reciprocal pivot denominators across
the 34-scalar provider domain. The first reciprocal is at 827589 and the
final unique pivot reciprocal is at 828556.

The same diagonal-address rule holds:

    pivot_diagonal_address = row_pointer[i] + 8*i

## Solver family

Both functions are fully unrolled fixed-layout symmetric pivot/elimination
routines. The source shows reciprocal pivots, normalized coefficient writes,
target-row subtraction, RHS accumulation and a descending solved-vector
elimination stage.

This places both implementations in the same broad algebraic family as the
already reconstructed builtin sparse LDL^T-style solver, but their storage and
operation schedule are specialized and unrolled. Phase 436 therefore records
the exact geometry without replacing every source expression with generated
code.

## Validation

The machine-readable runtime verifies one unique reciprocal pivot per scalar
and the diagonal-address formula for all 40/34 pivots.
