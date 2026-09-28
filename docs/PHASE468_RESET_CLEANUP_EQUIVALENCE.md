# Phase 468 — reset/cleanup storage partition (corrected by Phase 479)

## Goal

Phase 468 compared the source-backed cleanup coverage with the reset helper writes. Phase 479 corrected the comparison to distinguish **reset-zero writes** from **unit-diagonal seed writes**.

## Correct relation

For each provider:

`cleanup-covered storage = reset-zero slots ∪ unit-diagonal seed slots`

The two reset sets are disjoint.

Provider 0:

- cleanup-covered storage: **410 doubles** across workspace + output;
- reset-zero storage: **370 doubles**;
- unit-diagonal seeds: **40 doubles**;
- `370 + 40 = 410`;
- reset-zero is a subset of cleanup coverage;
- each diagonal seed lies in cleanup coverage and outside reset-zero.

Provider 1:

- cleanup-covered storage: **314 doubles** across workspace + output;
- reset-zero storage: **280 doubles**;
- unit-diagonal seeds: **34 doubles**;
- `280 + 34 = 314`;
- reset-zero is a subset of cleanup coverage;
- each diagonal seed lies in cleanup coverage and outside reset-zero.

## Interpretation

The cleanup function establishes a broader zero baseline. The selector-driven reset then writes zero to a subset of those slots and writes one exact `1.0` seed into one diagonal slot for each selector case.

Therefore it is incorrect to describe the reset function itself as recreating the full cleanup zero set. The stronger and correct statement is that its zero-write set plus its unit-diagonal seed set reconstruct the cleanup-covered storage domain.

## Scope boundary

This is a storage-level identity. It does not assign matrix semantics to any slot and does not imply that reset is a per-frame initializer.
