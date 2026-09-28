# Phase 501 — specialized-provider source mutation correlation

## Goal

Phase 501 joins the existing pre/post provider storage differential with the
source-derived factor edge contract. It maps each source edge `(pivot, column)`
through the observed row-pointer table:

    address = row_pointer[pivot] + 8 * column

The resulting absolute workspace addresses are compared with addresses that
actually changed between `provider_pre_*` and `provider_post_*` captures.

## Contract

`SHIFT.SpecializedProviderCaptureSourceMutationCorrelation/1`

The report distinguishes:

- source-pattern addresses observed to change;
- observed workspace addresses with no source factor edge;
- source-pattern addresses that did not change;
- alias addresses where multiple source edges resolve to one absolute address.

A multiple-edge address remains an alias set. The report never selects a unique
logical owner for an aliased storage slot.

## CLI

    python tools/compare_specialized_provider_mutations.py \
      --pre provider_pre_0_000001.json \
      --post provider_post_0_000001.json \
      --source SHIFT.exe.c \
      --provider 0 \
      -o mutation_correlation.json

Absolute/relative tolerances are forwarded to the existing raw capture diff:

    --abs-tol 1e-12 --rel-tol 1e-9

## Status semantics

`ready` means the required storage and provenance inputs were structurally valid.
`status=correlated` means every observed workspace mutation address was covered
by at least one source-derived factor edge.

`status=partial` means the analysis is valid but at least one observed workspace
mutation address is not covered by the factor pattern.

Neither status is numeric parity. Uncovered mutations can belong to other
source writes, and covered addresses do not establish semantic ownership.

## Scope boundary

The correlation layer does not:

- convert packed workspace aliases into a logical matrix;
- assign physical meaning to doubles;
- claim retail/provider numeric equality;
- replace an authentic runtime capture.

A real pre/post provider frame remains required for measured retail/provider
numerical differential.
