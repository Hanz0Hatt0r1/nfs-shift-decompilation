# Phase 452 — specialized-provider update relation IR

## Goal

Phase 452 turns the contextual assignment graph into a smaller reconstruction-oriented relation layer.

The IR separates normalized-factor relations, self-updates, generic subtractive updates, output-vector RHS updates, and other source-visible assignments.

## Relation forms

`normalized-factor`
— a multiplicative/pivot-scale assignment with at least one workspace RHS source. When exactly one workspace source is present, it is exposed as `factor_source`.

`self-update`
— a subtract-product assignment whose first RHS storage address is identical to the destination address.

`self-update-then-scale`
— the scaled counterpart of the same source-address relationship.

`subtractive-update`
— subtract-product shape without a proven self-reference.

`rhs-update`
— assignment whose destination is the solver output vector.

## Reconstruction value

Each relation preserves:

`pivot + source_line + loop_index + destination + ordered RHS dependencies + operator`

This provides the minimal structural unit needed for a future numeric executor while keeping the retail arithmetic itself outside the repository.

## Interpretation boundary

Self-reference is defined only by absolute-address equality. It is not treated as proof of a named mathematical operation. Packed workspace aliasing remains explicit from Phase 448–450.

Numeric coefficients, physical units, semantic matrix labels, provider C++ identities, and final BMW provider selection remain unresolved.

Run locally with:

    python specialized_provider_update_relations_runtime.py SHIFT.exe.c
