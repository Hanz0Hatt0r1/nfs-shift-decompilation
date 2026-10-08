# Process 1B — close the remaining direct `FUN_00481e20` bulk-copy alias

## Blocker

`P1.3.manager374` had one direct embedded-subobject destination left after the participant path was rejected:

```text
0x0081d335 -> FUN_00481e20
             destination = parent + 0x2d0
```

## Parent identity

The caller is `FUN_0081d2b0`. The repository already contains the source-order runtime boundary `SHIFT.CameraViewUpdatePipelineRuntime/1`, which identifies this function as the large per-frame `CCameraView` update and records the same `FUN_00481e20` action with target `+0x2d0`. The same runtime boundary records adjacent camera-view state at `+0x2e0..+0x2f4` and the owning camera-manager reference at `+0x44`.

The manager singleton under investigation is independently proven as `FUN_00489ad0() == 0x00bc9fc0`, constructed by `FUN_00488dc0` with vtable `0x00ab9190`. Its bounded virtual surface does not contain `FUN_0081d2b0`.

The Google Drive Ghidra export corroborates the navigation boundary: callsite `0x0081d335` is a direct call from `FUN_0081d2b0` to `FUN_00481e20`; heuristic vtable `0x00b16408` contains `FUN_0081d2b0` at slot 6. The vtable candidate is navigation-only and is not used as the semantic authority.

Therefore the destination on this path is camera-view-owned `+0x2d0`, not the fixed manager singleton root.

## Result

The direct `FUN_00481e20` bulk-copy literal-writer surface for `manager+0x374` is closed:

```text
FUN_0070dcc0 surface  -> rejected: stack-local destinations
0x004848f5            -> rejected: SMS participant+0xa00 render snapshot
0x0081d335            -> rejected: CCameraView+0x2d0 state
```

This does **not** prove `manager+0x374 == HDVehicle+0x4330`, and it does not eliminate helper-mediated, escaped-alias, computed-offset, or non-vtable indirect mutations.

## Handoff

Process 1B should now stop rescanning the direct `FUN_00481e20` surface and continue with exact singleton-root helper/alias/indirect mutation paths. Process 1D retains ownership of camera-follow semantics; this proof only reuses an already-existing camera-view ownership boundary to reject a false manager writer.
