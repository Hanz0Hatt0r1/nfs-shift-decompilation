# Phase 458 — factor-pattern admissibility gate

## Goal

Phase 458 closes a correctness hole in the experimental numeric executor. A source-derived factor pattern is evidence about retail storage/update topology, but it is not by itself proof that an arbitrary logical matrix can be factorized with that pattern.

## Gate

`compare_factor_pattern()` first performs an independent dense `LDLᵀ` factorization. It then extracts the computed strict-upper `(pivot,column)` support and compares it with the expected source-derived factor mask.

Only an exact support match is considered admissible. Missing or extra factor edges prevent guided execution.

`solve_guided()` enforces this gate before invoking the sparse-guided numeric solver.

## Why this is important

Without the gate, a mismatch between source topology and a test matrix could silently force coefficients to zero and produce a plausible-looking but incorrect result. The new design fails closed instead.

## Validation

Tests cover:

- extraction of lower-factor support into `(pivot,column)` coordinates;
- exact acceptance of a matching dense factor pattern;
- rejection when the matrix contains an extra factor edge;
- rejection of guided solve when the pattern is inadmissible.

## Interpretation boundary

The gate proves only numerical compatibility between a supplied logical matrix and a structural factor mask. It does not prove equivalence with the retail packed workspace or retail execution order.

The specialized-provider factor masks remain candidates for this gate until a real captured runtime matrix passes it.
