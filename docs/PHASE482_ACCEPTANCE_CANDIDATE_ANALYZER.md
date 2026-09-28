# Phase 482 — acceptance candidate analyzer

## Goal

Phase 482 adds a provider-neutral analyzer that runs one logical solver matrix against both recovered specialized-provider acceptance predicates.

## Input

The preferred input is the existing `SHIFT.SDFSolverCaptureRuntime/1` logical capture, or an explicit square matrix supplied by the caller.

## Output

`unique-match` — exactly one candidate provider's sparsity predicate matches.

`multiple-match` — more than one predicate matches.

`no-match` — no candidate predicate matches.

A provider dimension mismatch is retained in the per-provider result as `dimension-mismatch` and makes the overall analyzer `ready=false`; it is not silently converted into a sparsity mismatch.

## BMW seed boundary

The repository's BMW seed metadata records 40 scalars and 700 total nonzero matrix cells, i.e. 330 strict-upper nonzero cells after accounting for the 40 diagonal cells. Provider 0's acceptance signature expects 450 strict-upper nonzero cells, while provider 1 requires dimension 34.

The seed artifact does not store the full 40×40 matrix, so Phase 482 does not fabricate missing cell values to run the predicate. A future real capture can be passed directly through the analyzer.

## Scope boundary

The analyzer reports sparsity-predicate compatibility only. Even a unique sparsity match does not assign a provider class, prove BMW runtime selection, or establish numerical solver parity.
