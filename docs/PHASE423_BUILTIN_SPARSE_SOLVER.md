# Phase 423 — Exact builtin sparse solver

`FUN_007b0f20` now has an executable numerical implementation based directly on the full retail `SHIFT.exe.c` source.

## Factorization

For each scalar pivot `i`, the builtin path consumes the first forward item as the lower-dependency list. It updates the diagonal by subtracting the lower products, computes its reciprocal, then eliminates the current column from each later target row and stores the normalized factor in the upper cell.

## Forward substitution

The terminal forward record contains one item per scalar row. Its dependency bytes address already-normalized lower rows. Retail subtracts the corresponding matrix/RHS products and multiplies by the pivot reciprocal.

## Back substitution

The reverse table is traversed from `n-2` to `0`. Each dependency subtracts the corresponding upper-factor product from the current RHS entry. The last reverse record is allocated but not traversed.

## Validation

The kernel is regression-tested on 3×3 and 4×4 positive-definite systems and through the public `sdf_constraint_solver_runtime.solve_sdf_builtin()` wrapper. Provider virtual slot `+0x18` remains a separate backend. The first real retail 40-scalar capture is still required for exact runtime-state parity, because coefficient/RHS values are not synthesized from topology alone.
