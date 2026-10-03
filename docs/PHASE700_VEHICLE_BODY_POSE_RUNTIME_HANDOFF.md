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

The latest relevant merge is PR #1184,
`SHIFT.VehicleNamedBodyTopologyFrontier/2`. It supersedes the v1 topology
interpretation with already-committed Phase 404 archive evidence.

The exact retail BMW suspension SDF BODY order is now frozen as:

```text
0   body
1   fl_spindle
2   fr_spindle
3   fl_wheel
4   fr_wheel
5   rl_spindle
6   rr_spindle
7   rl_wheel
8   rr_wheel
9   fuel_tank
10  driver_head
```

Eight wheel/spindle vehicle fields therefore have exact SDF indices:

```text
fl_spindle = 1   fr_spindle = 2
fl_wheel   = 3   fr_wheel   = 4
rl_spindle = 5   rr_spindle = 6
rl_wheel   = 7   rr_wheel   = 8
```

The correction also proves that source/vehicle semantic field role `rear_axle`
at `vehicle+0x2e00` is **not** an SDF name. Its exact SDF BODY index remains
unresolved.

The exact non-wheel/spindle rows are now known:

```text
0   body
9   fuel_tank
10  driver_head
```

but none is promoted to chassis identity by name alone. The current Process 1
handoff deliberately remains:

```text
rear_axle_BODY_index_ready = false
main_chassis_BODY_selected = false
selected_BODY_index = null
vehicle_BODY_selection_ready = false
phase698_positive_selection_admissible = false
```

Three direct identity blockers remain:

1. `rear_axle` vehicle field role -> exact SDF BODY index;
2. main/chassis BODY semantic selection;
3. update-child -> vehicle solver-base continuity through `FUN_007615c0`.

Therefore current retail evidence still cannot produce a positive
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
