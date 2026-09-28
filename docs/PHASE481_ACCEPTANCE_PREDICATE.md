# Phase 481 — executable specialized-provider acceptance predicate

## Goal

Phase 481 makes the provider selection acceptance rule directly executable without requiring the retail source file at runtime.

The implementation consumes the already recovered static RLE signatures from `specialized_provider_runtime.py` and reproduces the strict-upper zero/non-zero comparison performed by the retail acceptance helpers.

## Predicate

For a matrix of the exact provider dimension:

`accepted iff every strict-upper cell has exactly the decoded RLE zero/non-zero state.`

The scan order is row-major over the strict upper triangle:

`(0,1), (0,2), …, (0,n-1), (1,2), …`

The comparison uses the same binary predicate as the retail code: `cell != 0.0`.

## Providers

Provider 0 uses dimension 40 and 83 RLE entries, yielding 780 strict-upper cells and 450 expected nonzero cells.

Provider 1 uses dimension 34 and 107 RLE entries, yielding 561 strict-upper cells and 315 expected nonzero cells.

## Diagnostics

On the first divergence the runtime reports:

- linear strict-upper index;
- exact `(row,column)`;
- expected and observed nonzero state;
- RLE run index and offset.

A dimension mismatch is reported separately and blocks the predicate result.

## Synthetic validation

The test suite builds a synthetic matrix directly from each recovered RLE signature. Both signatures accept their generated matrices. Single-cell changes and wrong dimensions are rejected with the expected status.

## Interpretation boundary

This phase proves only the source-backed sparsity predicate used by the provider acceptance functions. It does not prove that a particular matrix came from BMW M3 runtime state, does not identify provider class semantics, and does not reproduce provider numerical solving.
