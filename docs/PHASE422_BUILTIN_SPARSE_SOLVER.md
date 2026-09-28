# Phase 422 — Exact builtin sparse solver

`FUN_007b0f20` is now implemented as an executable numerical kernel rather than only a traversal contract.

## Factorization

For each scalar pivot `i`, the solver first updates the diagonal with the lower dependency products, computes the reciprocal diagonal, eliminates the current column from each later row, and stores the normalized factor in the upper-triangle cell. This matches the in-place sparse factorization performed by retail.

## Forward solve

The terminal forward record supplies the lower-dependency indices for each RHS entry. Retail subtracts the corresponding lower matrix coefficient times the already-normalized RHS entry, then multiplies by the pivot reciprocal.

## Back substitution

The reverse records are traversed from `n-2` down to `0`; each upper dependency subtracts `A[i][j] * rhs[j]`. The `n-1` reverse record is allocated but not traversed.

## Validation

The implementation is regression-tested on deterministic positive-definite systems and matches a standard dense reference solve to floating-point tolerance. The source graph record shape remains `n+1` forward records and `n` reverse records.

This closes the builtin numerical solver path. Provider virtual slot `+0x18` remains a separate opaque backend, and exact retail runtime equality still requires the live 40-scalar capture described by Phases 411–421.
