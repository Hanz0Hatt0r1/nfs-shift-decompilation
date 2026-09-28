# Phase 468 — reset/cleanup storage equivalence

## Goal

Phase 468 compares the source-backed cleanup coverage from Phase 467 with the reset writes extracted in Phase 466.

## Exact result

Provider 0:

- cleanup-covered storage slots: **410** across workspace + output;
- reset direct zero slots: **410**;
- unit-diagonal seeds: **40**;
- output zero sets: exact match;
- reset zero set and cleanup coverage: exact match;
- every diagonal seed lies inside the reset zero set.

Provider 1:

- cleanup-covered storage slots: **314** across workspace + output;
- reset direct zero slots: **314**;
- unit-diagonal seeds: **34**;
- output zero sets: exact match;
- reset zero set and cleanup coverage: exact match;
- every diagonal seed lies inside the reset zero set.

## Interpretation

The source evidence therefore supports a concrete storage initialization sequence:

`cleanup coverage → reset zero writes → overwrite pivot seeds with exact 1.0`

This is stronger than the Phase 456 read-before-write result because it describes the actual reset operation, not merely the first read observed by the solver.

## Important boundary

The equality is storage-level. It does not prove that the cleared/seeded storage is a complete logical matrix or identify physical quantities. The packed workspace still has aliasing, and provider semantics remain separate.

## Next use

A real Phase 463 provider capture can now be compared against a source-backed reset baseline: deviations from the 0/1 reset profile become direct evidence of what the caller populates before entering the provider solve.
