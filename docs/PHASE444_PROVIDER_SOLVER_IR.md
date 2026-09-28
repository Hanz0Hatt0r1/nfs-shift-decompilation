# Phase 444 — specialized-provider solver reconstruction IR

## Goal

Phase 444 joins the previous specialized-provider evidence layers into a single machine-readable reconstruction program.

For each pivot block the IR records the proven static row pointer and diagonal location, then attaches assignment-level destinations, normalized RHS dependencies, and operator signatures.

## Source layers

`SHIFT.SpecializedProviderSolverPivotRuntime/1`
→ fixed pivot geometry and diagonal addresses.

`SHIFT.SpecializedProviderUpdateGraph/1`
→ workspace write destinations.

`SHIFT.SpecializedProviderRHSStencilRuntime/1`
→ normalized RHS workspace/output/global references.

`SHIFT.SpecializedProviderDependencyGraphRuntime/1`
→ deduplicated workspace data-dependency edges.

`SHIFT.SpecializedProviderOperatorSignatureRuntime/1`
→ visible arithmetic-shape classification.

## Result

The combined structure is effectively:

`pivot -> assignment -> destination + dependencies + operator shape`

This is a stable intermediate representation for generating a neutral fixed-layout solver later. The IR deliberately does not contain the proprietary RHS expression text.

## Validation

Both provider domains remain explicit:

- provider 0: 40 pivot blocks;
- provider 1: 34 pivot blocks.

Validation rejects missing pivot blocks, non-sequential pivot ordering, missing workspace coordinates, missing operator signatures, and inherited errors from the Phase 441/442 source-derived layers.

## Interpretation boundary

The IR is structural and address-based. It does not assign PhysX class names, physical units, semantic matrix names, or a final provider identity for the BMW runtime. Numeric solver replacement remains capture-gated until the actual populated runtime state is observed.

Run locally with:

    python specialized_provider_solver_ir_runtime.py SHIFT.exe.c

The repository does not contain the proprietary retail source.
