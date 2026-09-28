# Phase 450 — specialized-provider contextual dependency graph

## Goal

Phase 450 applies the Phase 449 source-context resolver to assignment and RHS dependencies from the specialized provider solvers.

The result distinguishes two fundamentally different cases: an explicit loop/array address with a known provider row-pointer base, and a bare packed absolute address whose logical owner is ambiguous.

## Destination resolution

For loop-pointer and array-form destinations, the resolver uses the registered row-pointer base and `local_10` to produce one `(row,column)` coordinate. This is source context, not an inferred semantic matrix label.

For direct `DAT_...` destinations, the resolver consults the Phase 448 alias map. When multiple logical candidates share the address, every candidate is preserved.

Unknown loop bases fall back to the absolute-address domain instead of manufacturing a provider row.

## RHS resolution

RHS workspace references that explicitly originate from row-pointer expressions retain their contextual row/column interpretation. Bare workspace references are enriched with their alias candidate list.

Output-vector and unrelated global references remain separate domains.

## Why this matters

This prevents a subtle failure mode where a packed absolute address is silently assigned to the first row segment that contains it. The solver reconstruction can now carry both the exact retail address and the evidence used to choose a logical coordinate.

## Scope boundary

Phase 450 still does not assign semantic matrix meaning, provider class identity, physical units, or numerical coefficients. It establishes only source-context ownership information suitable for the next solver reconstruction layer.

Run locally with:

    python specialized_provider_contextual_dependency_runtime.py SHIFT.exe.c
