# Phase 698 — fail-closed vehicle/BODY pose selection

## Playable-slice blocker reduced

Phase 697 leaves the deepest native vehicle path with persistent retail-shaped
BODY bytes plus typed origin/basis snapshots after every successful explicit
outer update. The remaining transform-side blocker is no longer byte decoding;
it is identity:

```text
persistent BODY pose snapshots
  + exact concrete vehicle/update-object -> BODY identity
  -> select one BODY pose
  -> prove vehicle/world transform convention
  -> scene/camera/render transport
```

Process 1 PR #1176 (`SHIFT.VehicleBodyIdentityFrontier/1`) narrows that identity
problem but intentionally keeps the current handoff blocked:

```text
vehicle_BODY_selection_ready = false
selected_BODY_index = null
selected_BODY_pointer = null
update_child_to_BODY_identity_proven = false
vehicle_world_transform_mapping_proven = false
```

Phase 698 adds the Process 2 side of that future join without inventing the
missing index. It is reusable infrastructure for the nearest playable-slice
blocker: a positive future Process 1 selection can enter the persistent native
runtime without changing the physics chain again.

No original `SHIFT.exe` execution and no new runtime capture are used.

## Native contract

New format:

```text
SHIFT.NativeVehicleBodyPoseSelection/1
```

Files:

```text
native_runtime/include/shift_vehicle_body_pose_selection.hpp
native_runtime/src/vehicle_body_pose_selection.cpp
```

The selection input is deliberately narrow:

```text
VehicleBodyIdentitySelection
  selection_proven : bool
  body_index       : u32
```

The output is only the selected existing persistent pose:

```text
SelectedVehicleBodyPose
  body_index
  snapshot_generation
  origin : f64 x3
  basis  : f32 x9
```

No matrix conversion is performed.

## Fail-closed selection rules

`select_proven_vehicle_body_pose()` rejects before returning a pose when:

- `selection_proven` is false;
- the persistent snapshot generation differs from `explicit_update_count`;
- the persistent snapshot set is empty;
- the selected BODY index is outside the snapshot domain;
- the selected snapshot's embedded `body_index` differs from the requested index;
- any selected origin or basis component is NaN/Inf.

A successful selection copies the already-validated Phase 695/697 origin and
basis exactly. It does not normalize, transpose, remap, reinterpret or integrate
them.

## Process 1 artifact oracle

Reference gate:

```text
src/physics/vehicle_body_pose_selection_runtime.py
```

The Python oracle consumes the exact current Process 1 artifact format:

```text
SHIFT.VehicleBodyIdentityFrontier/1
```

A positive selection requires both:

```text
handoff.vehicle_BODY_selection_ready == true
scope.update_child_to_BODY_identity_proven == true
```

and a non-negative integer:

```text
handoff.selected_BODY_index
```

The current PR #1176 artifact therefore fails closed. The regression includes a
synthetic future-positive artifact only to freeze the Process 2 transport shape;
it is not evidence that retail BODY identity is currently proven.

## Persistent runtime relationship

The native regression initializes an actual `NativeRuntimeState` BODY buffer via
the existing Phase 695 path and selects from:

```text
runtime.outer_update.body_pose_snapshots
runtime.outer_update.body_pose_snapshot_generation
runtime.outer_update.explicit_update_count
```

Thus Phase 698 is attached to the real persistent runtime-owned pose transport,
not to a parallel synthetic pose representation.

Phase 698 does not add an automatically populated `vehicle_body_index` field to
`NativeRuntimeState`. Doing that before a positive Process 1 artifact would turn
a future evidence input into an implicit guessed default.

## Process 3 boundary

Process 3 PR #1179 (Phase 641) further reduces renderer bootstrap blockers by
exhausting existing capture sampler snapshots before considering recapture. The
prepared native scene side therefore continues to advance independently.

That renderer work does not establish which scene object is the concrete vehicle
for the selected physics BODY. Phase 698 consequently performs no write to a
scene matrix, Vulkan push constant, camera state or renderer object.

The remaining cross-domain join is explicitly:

```text
positive Process 1 BODY selection
+ Phase 698 selected persistent BODY pose
+ proven Process 3 vehicle scene-object identity
+ proven BODY pose -> vehicle world-transform convention
-> renderer/camera transport
```

## Scheduling and machine-scalar guards

Phase 698 does not alter the Phase 697 execution path. In particular it does not:

- attach explicit outer update to `fixed_step()`;
- infer cadence from the current scheduling frontier;
- replace any `FUN_007682c0` or `FUN_007afdd0` machine-scalar provider;
- introduce `std::sqrt`, `std::sin` or `std::cos` as retail machine substitutes.

The new selector uses `std::isfinite` only for fail-closed validation of values
already produced by the persistent pose path.

## Regression

Python:

```text
tests/test_vehicle_body_pose_selection_runtime.py
```

It verifies:

- the current PR #1176 shape fails because BODY selection is not proven;
- a synthetic positive identity selects exactly the requested snapshot;
- identity proof and explicit BODY index are independently mandatory;
- snapshot generation must match persistent explicit-update state;
- snapshot/body-index mismatch fails closed;
- NaN/Inf fails closed;
- world-transform, renderer, camera and scheduling claims remain false.

Native:

```text
shift_runtime_vehicle_body_pose_selection_check
```

It verifies:

- Phase 695 snapshots are created by `NativeRuntimeState` initialization;
- an unproven selection is rejected;
- a proven synthetic index selects byte-derived BODY 1 origin/basis unchanged;
- generation mismatch is rejected;
- out-of-domain BODY index is rejected;
- embedded snapshot identity mismatch is rejected;
- non-finite pose is rejected;
- no world-transform/renderer/camera/scheduling promotion is emitted.

## Provider/blocker inventory after Phase 698

| Boundary | Status | Next owner/action |
| --- | --- | --- |
| persistent BODY origin/basis snapshots | native persistent runtime | closed |
| Process 2 proven-index selection transport | fail-closed selector implemented | closed as infrastructure |
| current concrete vehicle -> BODY selection | PR #1176 explicitly not ready | Process 1 static proof |
| BODY pose -> vehicle world transform convention | blocked behind selected BODY | Process 1 |
| selected BODY -> prepared renderer vehicle object | cross-domain identity unproven | Process 1 + Process 3 |
| `FUN_007682c0` typed effect production | external provider | Process 1 machine/input proof |
| `FUN_007682c0` BODY `+0x50` application identity | external consumer | Process 1 BODY identity proof |
| `FUN_007afdd0` four f32 scalars | external provider | Process 1 machine scalar proof |
| remaining `FUN_0076d100` generic producers | evidence-gated | Process 1 producer mapping |
| outer-update cadence owner | unproven | keep explicit |

## Next blocker

The highest-value next Process 2 step is conditional on upstream proof. When
Process 1 promotes `vehicle_BODY_selection_ready` with an exact BODY index,
Phase 698 can immediately select the live persistent pose. The next implementation
must then consume a separately proven BODY-origin/basis -> vehicle world-transform
mapping and a proven renderer scene-object identity; it must not infer those from
matrix shape or object proximity.
