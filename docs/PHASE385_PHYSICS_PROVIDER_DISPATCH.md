# Phase 385 — Physics provider dispatch

`FUN_007b3820` now has a neutral runtime contract for the provider-selection branch that follows SDF/body matrix construction.

## Selection

`FUN_007d2e70(0)` returns `DAT_00c23da8`; if its `+0x14` virtual acceptance probe rejects the current `physics_system+0x3c` row table, `FUN_007d2e70(1)` returns `DAT_00c23dac`. A subsequent selector index returns null and enters the generic graph-construction path.

## Accepted-provider rewrite

The accepted provider releases the old matrix at `+0x38`, releases the row table at `+0x3c`, then replaces `+0x3c`, `+0x40` and `+0x44` through vtable offsets `+0x0c`, `+0x04` and `+0x08`. Its `+0x2c` call stores the provider/auxiliary result in `+0x48`. The same post-provider per-body allocation path then derives node-index vectors and per-body graph storage.

## Generic fallback

When no provider accepts the row table, `FUN_007b2010` rebuilds the body matrix and `FUN_007b1360` produces the compact graph allocation at `+0x40`. Each body receives allocations sized from `node_count`: `node_count*node_count*8` bytes for the matrix, `node_count*8` for row storage and `node_count*4` for the derived index vector. The source computes each derived index as `(row_pointer[i] - matrix_base) >> 3`.

## Explicit unknowns

Provider acceptance results are runtime-dependent. Concrete provider classes, the semantic type of replacement storage and the higher-level meaning of the compact graph remain unresolved.
