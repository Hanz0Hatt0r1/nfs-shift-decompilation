# Phase 454 — acceptance mask vs factor topology

## Goal

Phase 454 formally separates two structures that initially looked like candidates for the same solver graph:

- the provider acceptance helper's strict-upper sparsity mask;
- the source-derived normalized-factor destination topology produced by the provider solve function.

## Retail-derived comparison

Provider 0 acceptance mask contains 450 strict-upper cells, while the current source-derived factor topology contains 329 logical `(pivot,column)` factor edges.

Provider 1 acceptance mask contains 315 strict-upper cells, while the source-derived factor topology contains 245 factor edges.

These sets are intentionally reported as **distinct structural domains**. Their difference is not treated as a reconstruction failure: the acceptance helper checks the sparsity of its input matrix, whereas factor topology describes writes performed during the specialized solve.

## Why this matters

Equating the two masks would incorrectly force solver storage writes to match the provider's input sparsity test. The new contract preserves both layers and makes the relationship descriptive only.

## Interpretation boundary

Factor-edge coordinates remain source-derived implementation topology. Acceptance edges remain the provider's strict-upper probe mask. Neither is assigned a physical meaning, provider C++ class, or BMW identity.

The next reconstruction step can therefore focus on how the provider solver transforms accepted matrix state into its packed factor/output workspace, rather than trying to make the two static graphs identical.

Run locally with:

    python specialized_provider_acceptance_factor_separation_runtime.py SHIFT.exe.c
