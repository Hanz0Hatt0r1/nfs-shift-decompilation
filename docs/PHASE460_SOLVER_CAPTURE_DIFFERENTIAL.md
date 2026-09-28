# Phase 460 — solver capture differential harness

## Goal

Phase 460 connects the experimental numeric executor to the existing `SHIFT.SDFSolverCaptureRuntime/1` capture schema.

The harness consumes a normalized pre-solve capture (`scalar_count`, `matrix`, `rhs`) and optionally a real post-solve vector. It runs the experimental executor and compares the predicted vector with the captured result using the repository's existing absolute/relative tolerance logic.

## Status model

`predicted-only`
— the executor produced a numerical result, but no post-solve capture was supplied. This is not parity.

`matched`
— predicted and captured vectors agree within the requested tolerances.

`numeric-divergence`
— both vectors are present but at least one cell exceeds tolerance. The report includes mismatch count and maximum absolute/relative error.

`blocked`
— capture schema or executor prerequisites failed.

## Provider-aware mode

When a source-derived factor edge set is supplied, the harness uses Phase 458's factor-pattern admissibility gate before entering sparse-guided execution. A structural mismatch therefore blocks rather than silently zeroing factor entries.

## Interpretation boundary

A numerical match is evidence for the supplied logical matrix and executor model only. It does not prove binary equivalence with the retail provider. A mismatch can come from logical matrix extraction, packed workspace mapping, initial-state construction, exact retail update ordering, or solver algebra.

Provider-backend captures remain a distinct track because the existing builtin probe path can be bypassed by a provider backend.

Run the module tests with:

    python -m pytest tests/test_specialized_provider_capture_differential_runtime.py
