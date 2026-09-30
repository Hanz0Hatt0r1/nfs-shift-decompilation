# Phase 551 — SGB root-transform state and SceneGraph transport

Phase 551 closes the transport boundary left by Phase 550. It does not guess a
root transform. Instead it models the two source-backed states of a
LOD/HIERARCHY MultiMatrix and makes update-history knowledge explicit.

## Constructor state

`FUN_0068cbb0` builds a local MATRIX and immediately copies it into the
matching world slot. Therefore, immediately after construction:

```text
world[0] = local[0]
```

This is a proven initial state, not a promise that the slot remains unchanged
for the lifetime of the runtime object.

## SceneGraph transform transport

The retail x86 code resolves the previously ambiguous producer path:

- `FUN_0068bc60(sceneGraph, object, matrix)` forwards `matrix` in EDX to
  `object->vfunc(+0x2c)` when updates are immediate.
- In deferred mode it enqueues update type 4 through `FUN_0068ba90`.
- Type 4 reserves an entry in the dedicated transform pool and copies exactly
  `0x40` bytes with `FUN_00401d10`.
- `FUN_0068b840` later resolves `xform_pool + index * 0x40` into EDX and
  calls the queued object's vfunc `+0x2c`.
- HIERARCHY `FUN_006ab710` and LOD `FUN_006b4280` both copy that matrix into
  MultiMatrix world slot 0 and run `FUN_006b1620`.

So a SceneGraph transform update **replaces** the root; it is not multiplied
with serialized slot 0.

## State contract

`src/scene/sgb_root_transform.py` adds
`SHIFT.SGBRootTransformState/1`.

The contract distinguishes three cases:

- update history unknown: constructor state is reported as evidence, but current
  root remains blocked;
- update history known empty: current root is the constructor world slot 0;
- one or more updates known: current root is exactly the last 4x4 update.

This distinction is required for static/offline analysis because the binary SGB
loader `FUN_006a4b40` creates descriptors/runtime payloads but does not itself
emit a SceneGraph transform update.

## Remaining boundary

The arithmetic and transport are now source-backed. Final RenderBinding
admission still needs per-instance knowledge of whether a concrete scene object
received transform updates (or a captured update stream). Missing history stays
fail-closed.
