# Phase 442 — specialized-provider address dependency graph

## Goal

Phase 442 consumes the Phase 441 RHS stencils and collapses repeated assignment references into a machine-readable address-level data-dependency graph.

For every assignment, the contract keeps the destination and separates RHS reads into workspace cells, output-vector indices, and unresolved global addresses.

## Dependency representation

A workspace edge is represented as:

`source workspace cell -> assignment destination`

with the pivot index preserved. Duplicate source/destination pairs within the same pivot are collapsed in the graph edge set while the original assignment-level nodes remain available.

Workspace relationships are classified structurally as:

- `prior-pivot` — source row precedes the current pivot;
- `current-pivot` — source row equals the pivot;
- `destination-row` — source row is the destination row;
- `future-pivot` — source row lies after the pivot but before the destination row;
- `later-row` — source row lies beyond the destination row.

Non-workspace reads retain their domain and are not forced into the workspace graph.

## Validation

The graph inherits Phase 441 validation, which in turn cross-checks workspace destination counts against Phase 440. Additional validation requires every workspace reference to carry a valid row/column coordinate and requires all workspace rows to remain inside the provider scalar domain.

## Interpretation boundary

This is an **address dependency graph**, not a semantic sparse-matrix graph. The graph says which static data cells are referenced by an assignment; it does not assign matrix meaning, operator type, physical units, or provider class identity.

The next reconstruction layer can use these exact dependencies to group assignments into forward-update and back-substitution templates while keeping all retail numeric expressions outside the repository.

## Local audit

Run against the supplied local retail decompilation source with:

    python specialized_provider_dependency_graph_runtime.py SHIFT.exe.c

The executable contract covers both fixed-layout solvers: provider 0 (40 scalars) and provider 1 (34 scalars).
