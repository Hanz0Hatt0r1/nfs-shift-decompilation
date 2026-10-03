# Phase 700 — NativeRuntimeState vehicle/BODY pose handoff

## Playable-slice blocker reduced

Phase 698 provides a fail-closed selector from a future proven BODY index to one
persistent BODY origin/basis snapshot. Phase 699 proves there is currently no
additional physics producer safe to internalize and freezes the exact nine
Process 1 handoffs still required by the deepest Phase 697 outer chain.

Phase 700 closes the next transform-side integration gap:

```text
NativeRuntimeState
  -> ready physics workspace
  -> admitted participant identity
  -> initialized persistent outer-update state
  -> exact BODY/snapshot cardinality
  -> Phase 698 proven BODY selection
  -> exact selected persistent BODY pose
```

This makes the selector consume the real runtime-owned persistent pose state
instead of an arbitrary snapshot collection. It does not invent the still
missing retail chassis BODY identity or world-transform convention.

No original `SHIFT.exe` execution and no new runtime capture are used.

## Native contract

```text
SHIFT.NativeVehicleBodyPoseRuntimeHandoff/1
```

Files:

```text
native_runtime/include/shift_vehicle_body_pose_runtime_handoff.hpp
native_runtime/src/vehicle_body_pose_runtime_handoff.cpp
```

Entry point:

```text
build_vehicle_body_pose_runtime_handoff(
    const NativeRuntimeState& runtime,
    const VehicleBodyIdentitySelection& selection)
```

Result:

```text
SelectedVehicleBodyPose pose
runtime_body_count
explicit_update_count
```

The selected pose is copied exactly from the Phase 695/697 representation:

```text
origin : f64 x3
basis  : f32 x9
```

No world matrix, axis remap, transpose, handedness conversion or normalization is
performed.

## Runtime admission

Before Phase 698 selection is called, Phase 700 requires:

- `physics.workspace.ready == true`;
- `physics.participant_ready == true`;
- `physics.participant_identity_join_proven == true`;
- `outer_update.initialized == true`;
- `outer_update.body_count == physics.workspace.body_count`;
- `outer_update.body_pose_snapshots.size() == outer_update.body_count`.

Phase 698 then still requires:

- an explicit positive BODY identity proof;
- an in-domain BODY index;
- pose generation synchronized with `explicit_update_count`;
- embedded snapshot/body identity equality;
- finite origin and basis values.

The handoff is read-only. It does not mutate BODY bytes, snapshots, generation,
participant state or scheduler state.

## Process 1 boundary

The latest relevant merge is PR #1183,
`SHIFT.VehicleNamedBodyTopologyFrontier/1`.

It proves:

- nine named BMW wheel/spindle/rear-axle BODY field roles;
- exact retail BMW suspension SDF cardinality of 11 BODY records;
- an optional exact hash-matched SDF path that can recover BODY name order and
  finite residual rows.

It deliberately keeps:

```text
main_chassis_BODY_selected = false
selected_BODY_index = null
vehicle_BODY_selection_ready = false
vehicle_world_transform_ready = false
```

and leaves two identity joins open:

1. main/chassis BODY semantic selection;
2. update-child -> vehicle solver-base continuity through `FUN_007615c0`.

Therefore current retail evidence cannot produce a positive
`VehicleBodyIdentitySelection` for Phase 700. The synthetic positive index in the
regression freezes only the downstream Process 2 transport contract.

## Process 3 boundary

Process 3 Phase 642 preserves validated runtime requirement admission across
renderer refresh and removes false resource-side blockers. This improves the
future resource-driven vertical-slice bootstrap but does not establish:

- physics BODY/vehicle -> exact scene-object identity;
- BODY basis/origin -> renderer world-transform convention;
- a camera follow target.

Phase 700 therefore has no scene, Vulkan or camera side effect.

## Phase 699 provider frontier preserved

Phase 700 does not change the `SHIFT.NativeVehicleExternalProviderFrontier/1`
result. All nine deepest Phase 697 producer boundaries remain external and
`implement_now` remains empty until new proof arrives.

In particular this phase does not internalize:

- `FUN_007675f0` caller inputs;
- `FUN_007682c0` effect production;
- `FUN_007682c0` BODY `+0x50` receiver identity;
- `FUN_007afdd0` machine scalars;
- `FUN_007b8810` refresh production;
- the `FUN_00765470` half-step refresh bundle;
- the remaining broad `FUN_0076d100` producer callbacks.

## Scheduling remains explicit

The native executable still drives its existing shell through
`native_state.fixed_step(intent)`. The deepest Phase 697 explicit outer update is
not attached to that loop by Phase 700.

Exact machine-callsite selection, dynamic statement multiplicity and runtime
cadence ownership are still evidence-gated, so Phase 700 keeps:

```text
fixed_step_auto_schedule = false
deep_outer_update_executable_schedule_enabled = false
```

No host `sqrt`, `sin` or `cos` is introduced at any unresolved machine-scalar
boundary.

## Reference oracle

```text
src/physics/vehicle_body_pose_runtime_handoff.py
tests/test_vehicle_body_pose_runtime_handoff.py
```

The oracle validates workspace/participant/outer-state admission and BODY
cardinality before delegating to the existing Phase 698 artifact selector. It
also freezes the negative scope for world transform, renderer, camera and
scheduling.

## Native regression

```text
shift_runtime_vehicle_body_pose_runtime_handoff_check
```

The regression uses the real `NativeRuntimeState` and the existing shared BODY
fixture. It verifies:

- handoff before persistent outer initialization fails;
- participant identity admission is mandatory;
- Phase 698 unproven selection remains rejected;
- a synthetic proven BODY 1 selection returns its exact stored origin/basis;
- BODY bytes, snapshots and snapshot generation remain unchanged by the handoff;
- generation mismatch fails closed;
- workspace/persistent BODY cardinality mismatch fails closed.

## Blocker graph after Phase 700

```text
persistent BODY bytes + typed pose snapshots        closed
  -> runtime workspace/participant admission        closed
  -> proven-index pose selection transport          closed as infrastructure
  -> NativeRuntimeState read-only pose handoff      closed as infrastructure
  -> exact retail main/chassis BODY index           blocked on Process 1
  -> BODY pose -> vehicle world-transform mapping   blocked on Process 1
  -> vehicle/BODY -> renderer scene object          blocked on Process 1 + Process 3 identity join
  -> scene/camera transform transport               blocked behind those proofs
```

The execution side remains separately blocked by the nine Phase 699 external
producers and the unproven outer-update cadence owner.

## Next Process 2 action

Implement another integration step only when a new upstream proof shortens one of
those blockers. Highest-value positive handoffs are:

1. exact main/chassis BODY index plus update-child -> solver-base continuity;
2. exact BODY pose -> vehicle world-transform convention and renderer object identity;
3. any Phase 699 producer promoted to `implement_now`;
4. exact outer-update callsite, dynamic multiplicity and cadence owner.
