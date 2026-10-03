# Camera dynamic-array release-pointer cross-check

`src/camera/camera_dynamic_array_runtime.py` models the recovered growth paths in
`FUN_00813080` and `FUN_008166b0`. Both paths already preserve the retail
`FUN_00886930` release-helper identity when old storage is released after copying.

The runtime contract can now optionally consume the same two memory evidence
artifacts used by `src/core/memory_pool_runtime.py`:

- `SHIFT-MEMORY-RETAIL-STATIC-SUMMARY/1`;
- `SHIFT-MEMORY-SOURCE-SEMANTIC-SUMMARY/1`.

When supplied, each growth result receives a separate
`memory_wrapper_evidence` block with format
`SHIFT.CameraDynamicArrayMemoryCrosscheck/1`.

## Promotion gate

The cross-check is ready only when all of the following are true:

1. the retail static summary independently proves the `released-pointer`
   physical role for `FUN_00886930`;
2. the source semantic summary independently exposes a consistent
   `released-pointer` source role for that helper;
3. the proven source argument index is `0`;
4. the exact growth caller is present in the proven caller set:
   - `FUN_00813080` for the 16-bit growth path;
   - `FUN_008166b0` for the 11-dword growth path.

The cross-check fails closed if any of those facts are absent or inconsistent.
Supplying only the source semantic summary is insufficient because
`build_memory_pool_contract()` requires the matching static physical proof before
promoting the source role.

## Backward compatibility

Without either optional summary, the returned dynamic-array JSON is unchanged:
no `memory_wrapper_evidence` key is added and the existing action remains:

```json
{"action": "FUN_00886930", "release_old_storage": true}
```

The evidence layer therefore strengthens the recovered contract without changing
its execution description.

## Scope boundary

This cross-check proves only that source argument 0 of the observed
`FUN_00886930` calls is the released pointer and that the two camera growth
functions occur among the proven callsites.

It does **not** prove:

- the complete release-helper ABI;
- that `DL` is a release/delete flag;
- delete or destructor kind;
- pool-selector semantics;
- ownership or reference-counting policy;
- scalar-delete versus array-delete semantics;
- compiler `operator delete` identity.

Those claims remain explicitly outside the current evidence boundary.
