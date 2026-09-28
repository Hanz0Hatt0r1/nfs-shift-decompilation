# Phase 457 — experimental specialized-provider numeric executor

## Goal

Phase 457 adds the first executable numerical model derived from the recovered solver structure. It implements a clean-room unit-lower `LDLᵀ` reference with the observed stages: reciprocal diagonal pivot, future-factor normalization, symmetric trailing update, forward solve, diagonal solve, and descending backward solve.

## Two modes

**Dense mode** (`factor_edges=None`) uses every strict-upper pair. It is a conventional numerical oracle for symmetric matrices.

**Sparse-guided mode** accepts an explicit `(row,column)` factor edge set. Missing edges are forced to structural zero. This is the experimental mode intended to consume source-derived provider factor topology.

## Validation

Regression tests cover:

- exact reconstruction of a known dense `L·D·Lᵀ` matrix;
- exact reconstruction of a sparse matrix whose `L` structure matches the supplied factor edge set;
- solve/residual verification against a known right-hand side;
- rejection of non-symmetric input;
- singular/near-singular pivot protection;
- explicit experimental-status metadata.

## Important boundary

The numerical core intentionally does **not** claim to reproduce the retail provider yet. The remaining unknowns are the packed-workspace mapping, exact per-assignment update order, numeric initialization of the workspace, and the relationship between the provider's accepted matrix state and its factor representation.

Therefore the module status is `experimental-numeric-reference`, not `retail-compatible`.

## Next use

The next step can feed the source-derived factor topology into this executor through a controlled adapter, then compare the resulting logical `L`/`D` behavior with runtime captures without changing the evidence layers.

Run tests with:

    python -m pytest tests/test_specialized_provider_experimental_numeric_runtime.py
