# Shared camera release-pointer cross-checks

`src/camera/camera_memory_release_evidence.py` centralizes the optional memory
semantic gate used by recovered camera contracts that call the retail release
helper `FUN_00886930`.

The gate consumes the same independent artifacts as
`src/core/memory_pool_runtime.py`:

- `SHIFT-MEMORY-RETAIL-STATIC-SUMMARY/1`;
- `SHIFT-MEMORY-SOURCE-SEMANTIC-SUMMARY/1`.

It reports a callsite ready only when all of the following agree:

1. the static summary proves the `released-pointer` physical role;
2. the source semantic summary proves the `released-pointer` role for
   `FUN_00886930`;
3. the stable source argument index is `0`;
4. the exact reconstructed camera caller occurs in the proven caller set.

## Current camera consumers

The shared gate is used by:

- `FUN_00813080` — 16-bit dynamic-array growth;
- `FUN_008166b0` — 11-dword dynamic-array growth;
- `FUN_008112b0` — `RenderCameraViewManager` deleting wrapper;
- `FUN_0081b140` — derived `CCameraView` deleting wrapper.

The dynamic-array paths retain their existing
`SHIFT.CameraDynamicArrayMemoryCrosscheck/1` output format. The deleting-wrapper
paths use `SHIFT.CameraDeletingWrapperMemoryCrosscheck/1`. Both formats are
backed by the same fail-closed implementation.

## Default behavior

When neither memory summary is supplied, no `memory_wrapper_evidence` key is
added. Existing action lists, conditions and helper identities therefore remain
unchanged.

In particular, the existing deleting-wrapper conditions such as
`(delete_flag & 1) != 0` or `param_1 & 1` are preserved as source-backed wrapper
behavior. The cross-check does **not** reinterpret those expressions as proof of
the meaning of the backend `DL` byte.

## Scope boundary

A ready cross-check proves the released pointer source argument and exact caller
membership only. It does not prove:

- the complete release-helper ABI;
- the semantic role of backend `DL`;
- delete/destructor kind;
- pool-selector semantics;
- ownership or reference counting;
- scalar-delete versus array-delete behavior;
- compiler `operator delete` identity.

Those remain outside the current evidence boundary.
