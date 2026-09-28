# Phase 440 — specialized-provider workspace update graph

## Goal

Phase 440 turns the retail FUN_007c7200 / FUN_007cdfc0 solver bodies into a
machine-readable **workspace-cell write graph**.

The implementation deliberately stops at the left-hand-side address boundary.
It does not copy proprietary right-hand-side expressions and does not assign
undocumented physical or C++ class semantics.

## What is reconstructed

For every unique reciprocal pivot, the extractor:

1. isolates the source block between consecutive pivot reciprocals;
2. resolves workspace writes whose destination is expressed as:
   - a direct DAT_xxxxxxxx = ... store;
   - *(double *)(&DAT_xxxxxxxx + local_10 * 8) = ...;
   - (&DAT_xxxxxxxx)[local_10] = ...;
3. maps the absolute destination address back into the exact provider row/column
   coordinate defined by the Phase 435 row-pointer topology;
4. groups writes into:
   - current-row future columns (the Phase 439 factor pattern);
   - current-row non-future columns;
   - future target rows;
   - prior rows.

The array form is resolved by **absolute address**, so an index that extends past
the current row segment is intentionally allowed to land in a later row segment.
This matches the static memory layout rather than treating each array base as an
independent matrix row.

## Cross-phase invariant

The factor columns recovered from the new writer resolver are compared against
the Phase 439 factor-pattern extractor for every pivot. A mismatch blocks the
contract.

The final pivot is treated specially: its source block contains the descending
solution stage, so prior-row workspace writes are expected there and are reported
rather than rejected.

## Interpretation boundary

The output is a structural **write graph**, not yet a semantic sparse-matrix
graph. A (pivot, target row, column) tuple says that the corresponding workspace
cell is written inside the pivot block; it does not by itself prove a mathematical
matrix edge.

Likewise, the graph intentionally omits the proprietary numeric RHS expressions.
The next reconstruction step can use these exact destinations together with the
source-level RHS reference patterns to recover the fixed-layout update stencils.

## Retail source audit

The extractor is designed to run directly against a local SHIFT.exe.c:

    python specialized_provider_update_graph_runtime.py SHIFT.exe.c

Both specialized providers must pass the integrated validation:

- provider 0: 40 pivots;
- provider 1: 34 pivots;
- Phase 439 factor-column cross-check must pass for every pivot;
- no prior-row workspace activity is accepted before the terminal pivot block.

The repository does not contain the proprietary retail source.
