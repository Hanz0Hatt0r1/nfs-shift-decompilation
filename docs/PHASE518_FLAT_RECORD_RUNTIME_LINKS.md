# Phase 518 — FLAT record runtime links

Phase 518 closes the remaining low-level FLAT direct-record link fields that are explicitly consumed by the retail tree indexer.

## Proven fields

`FUN_006af780` iterates direct records at `0x40`-byte stride. For each record:

- `record + 0x38` is read as the object/resource handle;
- `record + 0x3c` is read as the runtime child/index and is used to address the normalized runtime link table.

`FUN_006af830` also consumes `record + 0x38` as the handle being retained/released during tree teardown.

The existing `+0x1c` low-24-bit span and high-byte depth/termination marker remains unchanged.

## IR

`src/scene/flat_runtime.py` now exposes:

- `object_handle` from `+0x38`;
- `child_index` from `+0x3c`;
- the existing `runtime_index` and `index_word` aliases for compatibility.

The raw 16-dword record remains available, so no higher-level scene semantics are invented.

## Verification

`tests/test_flat_runtime.py` verifies that the new fields survive decoding and match the existing index word.

## Boundary

This proves record-to-runtime-link metadata only. The semantic class of the object referenced by `+0x38` remains intentionally unresolved.