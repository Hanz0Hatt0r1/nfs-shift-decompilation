# Phase 699 — NativeRuntimeState vehicle/BODY pose handoff

## Playable-slice blocker reduced

Phase 698 adds the fail-closed transport from a future proven concrete BODY index
to one persistent BODY origin/basis snapshot. That selector is deliberately
independent from the runtime owner so it can validate the Process 1 identity
artifact without implicitly claiming that any arbitrary snapshot set belongs to
the admitted native vehicle participant.

Phase 699 joins the selector to the existing `NativeRuntimeState` persistence
boundary:

```text
NativeRuntimeState
  -> ready physics workspace
  -> admitted participant identity
  -> initialized persistent outer-update state
  -> exact BODY/snapshot cardinality
  -> Phase 698 proven BODY selection
  -> selected persistent BODY pose
```

This removes one integration gap on the path to a vehicle world transform while
preserving the still-unproven retail identity and transform mappings.

No original `SHIFT.exe` execution and no new runtime capture are used.

## Native contract

New format:

```text
SHIFT.NativeVehicleBodyPoseRuntimeHandoff/1
```

Files:

```text
native_runtime/include/shift_vehicle_body_pose_runtime_handoff.hpp
native_runtime/src/vehicle_body_pose_runtime_handoff.cpp
```

The entrypoint is read-only:

```text
build_vehicle_body_pose_runtime_handoff(
    const NativeRuntimeState& runtime,
    const VehicleBodyIdentitySelection& selection)
```

It returns:

```text
SelectedVehicleBodyPose pose
runtime_body_count
explicit_update_count
```

The selected pose remains exactly the Phase 695/697 stored representation:

```text
origin : f64 x3
basis  : f32 x9
```

No world matrix is formed.

## Admission boundary

Before Phase 698 selection is called, the runtime handoff requires:

- `physics.workspace.ready == true`;
- `physics.participant_ready == true`;
- `physics.participant_identity_join_proven == true`;
- `outer_update.initialized == true`;
- `outer_update.body_count == physics.workspace.body_count`;
- `outer_update.body_pose_snapshots.size() == outer_update.body_count`.

Phase 698 then additionally requires:

- a positive external BODY identity proof;
- an exact in-domain BODY index;
- snapshot generation synchronized with `explicit_update_count`;
- exact embedded snapshot/BODY identity;
- finite origin and basis.

This order ensures a future positive Process 1 BODY selection cannot be applied
to an unadmitted participant or unrelated runtime BODY workspace.

## Current Process 1 boundary

The latest Process 1 merge used by this phase remains PR #1176,
`SHIFT.VehicleBodyIdentityFrontier/1`.

It explicitly reports:

```text
vehicle_BODY_selection_ready = false
selected_BODY_index = null
update_child_to_BODY_identity_proven = false
vehicle_world_transform_mapping_proven = false
```

Therefore the current retail evidence still fails Phase 698/699 by design.
Phase 699 does not add a default BODY index, infer BODY 0, infer the first active
participant, or equate the outer receiver with the vehicle object.

## Current Process 3 boundary

The latest Process 3 merge at implementation time is PR #1179, Phase 641. It
exhausts already-existing capture sampler snapshots before a renderer recapture
would be considered and can advance the prepared native-scene resource path.

That work remains renderer/resource evidence. It does not identify the concrete
vehicle scene object corresponding to a physics BODY. Phase 699 therefore does
not write its selected pose into a scene node, draw instance, push constant, or
camera target.

## Runtime executable boundary

The native executable currently drives its frame/input shell through:

```text
native_state.fixed_step(intent)
```

The deepest Phase 697 explicit outer-update entrypoint is not automatically
called by that loop. Phase 699 does not change that.

This is intentional because several required outer-chain producers remain
external/evidence-gated:

- `FUN_007675f0` caller inputs;
- `FUN_007682c0` typed effect production;
- the four `FUN_007afdd0` f32 machine scalars;
- remaining `FUN_0076d100` producer callbacks;
- retail half-step/post-half-step refresh production;
- outer-update dynamic multiplicity/cadence ownership.

A `NativeRuntimeState` pose handoff is therefore a read-only consumer of already
committed explicit outer state; it is not permission to schedule the outer chain
from `fixed_step()` or the render loop.

## Reference oracle

Python runtime admission oracle:

```text
src/physics/vehicle_body_pose_runtime_handoff.py
```

Regression:

```text
tests/test_vehicle_body_pose_runtime_handoff.py
```

It verifies:

- workspace admission before selection;
- participant readiness and identity proof before selection;
- persistent outer-state initialization before selection;
- BODY/snapshot cardinality equality;
- delegation to the Phase 698 identity/generation gate;
- the current Process 1 not-ready state still fails closed;
- a synthetic future-positive identity returns exactly one existing pose;
- no runtime mutation, world transform, renderer, camera or scheduling claim.

The synthetic positive artifact freezes the future transport contract only. It
is not retail BODY identity evidence.

## Native regression

```text
shift_runtime_vehicle_body_pose_runtime_handoff_check
```

The test constructs the real `NativeRuntimeState`, configures the real workspace
boundary, admits the participant identity, and initializes persistent BODY bytes
through the existing Phase 695 path.

It verifies:

- handoff before persistent outer-state initialization fails;
- participant admission failure fails before BODY selection;
- an unproven BODY selection cannot bypass Phase 698;
- a synthetic proven BODY 1 selection returns its exact persistent origin/basis;
- the handoff does not mutate BODY bytes, pose snapshots or pose generation;
- snapshot-generation mismatch fails closed;
- workspace/persistent BODY cardinality mismatch fails closed.

## Negative scope

Phase 699 explicitly does **not** prove or enable:

```text
vehicle world transform                         false
basis transpose/axis/handedness conversion     none
renderer vehicle-object transport              false
camera follow target                            false
fixed-step outer-update scheduling              false
deep Phase 697 executable scheduling            false
machine scalar substitution                     false
```

No `std::sqrt`, `std::sin` or `std::cos` path is introduced. `std::isfinite`
remains confined to the already-merged Phase 698 fail-closed validation of a
selected stored pose.

## Blocker graph after Phase 699

```text
persistent BODY bytes + pose snapshots         closed
  -> runtime workspace/participant admission   closed
  -> proven BODY-index selection transport     closed as fail-closed infrastructure
  -> concrete retail vehicle -> BODY index     blocked on Process 1
  -> BODY pose -> vehicle world transform      blocked on Process 1
  -> vehicle BODY -> renderer scene object     blocked on Process 1 + Process 3 identity join
  -> scene/camera transform transport           blocked behind those proofs
```

The deepest physics execution path remains separately blocked from the real
executable loop by its unresolved producer boundaries and cadence owner.

## Next blocker

The next Process 2 implementation should consume whichever upstream positive
proof arrives first:

1. an exact Process 1 vehicle/update-object -> BODY index, enabling Phase 699 on
   retail evidence;
2. a proven BODY origin/basis -> vehicle world-transform convention plus renderer
   object identity, enabling scene/camera transport;
3. a proven remaining physics producer, replacing another injected Phase 697
   boundary;
4. proven outer-update dynamic multiplicity/cadence ownership, enabling exact
   scheduling at that boundary.

Until one of those becomes positive, Phase 699 should remain read-only and
explicitly unscheduled.
