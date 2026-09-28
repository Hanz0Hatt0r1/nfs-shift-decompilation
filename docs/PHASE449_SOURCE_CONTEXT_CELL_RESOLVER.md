# Phase 449 — specialized-provider source-context cell resolver

## Goal

Phase 449 turns the Phase 448 packed-workspace alias map into a resolver that respects the source expression's addressing form.

An explicit row-pointer base plus `local_10` index is treated as authoritative source context and resolves to one `(row,column)` coordinate. A direct absolute `DAT_...` address is never silently assigned a single logical owner when the packed storage contains aliases.

## Resolution rules

| Source form | Resolution |
|---|---|
| row pointer base + local index | unique workspace `(row,column)` |
| explicit array base + local index | unique workspace `(row,column)` when used with the current row-pointer context |
| direct workspace address | all candidate alias coordinates |
| output-vector address | output-vector index |
| unrelated address | unresolved global address |

## Verified invariants

The resolver covers the complete 40-scalar provider-0 and 34-scalar provider-1 domains. Every pivot diagonal `row_pointer[i] + 8*i` resolves uniquely through explicit source context and remains inside the factor workspace.

For provider 0, `0x00C21800` remains explicitly ambiguous as `(0,25)` or `(1,0)` when considered as a bare absolute address. The source-context form can instead distinguish the intended row by its pointer base and local index.

## Why this is the next reconstruction boundary

Phases 440–448 established that provider storage is packed and aliased. Phase 449 provides the missing bridge from source syntax to logical coordinate without inventing ownership for bare addresses.

This resolver is intended to feed the next step: exact pivot update stencils where every source assignment can carry both its absolute address and, when justified by source context, its logical coordinate.

Run with:

    python specialized_provider_source_context_resolver_runtime.py

or inspect one absolute address:

    python specialized_provider_source_context_resolver_runtime.py --provider 0 --address 0x00c21800
