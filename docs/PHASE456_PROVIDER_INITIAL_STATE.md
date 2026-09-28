# Phase 456 — specialized-provider initial-state analysis

## Goal

Phase 456 performs a source-order read-before-write analysis of the specialized provider solver state.

For every assignment, RHS references are classified as either already written earlier in the solver or `preexisting-or-external`. The analysis is keyed by the exact absolute storage address used by the retail source, avoiding assumptions about logical ownership of aliased packed cells.

## Resulting boundary

The report separates three classes of first-read state:

- packed workspace addresses that must already contain something before their first solver read;
- output-vector addresses that are read before being written by the solver;
- external/global addresses outside the provider workspace/output vector.

`preexisting-or-external` is intentionally conservative: it proves only that the address has not yet been written by this solver execution. It does not prove which earlier runtime function produced it.

## Why this matters

This is the first direct reconstruction of the **input-state boundary** of the specialized solver. A future numeric executor can use the resulting address set as the minimum initialization contract while keeping aliased storage and unknown upstream producers explicit.

## Interpretation boundary

Absolute-address liveness does not assign matrix semantics, physical units, provider C++ classes, or BMW provider identity. It is a source-order dataflow fact only.

Run locally with:

    python specialized_provider_initial_state_runtime.py SHIFT.exe.c
