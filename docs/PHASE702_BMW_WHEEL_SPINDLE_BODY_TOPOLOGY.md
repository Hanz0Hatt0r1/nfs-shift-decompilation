# Phase 702 — BMW proven BODY topology handoff

## Playable-slice blocker reduced

Phase 702 started from Process 1 PR #1184 / `SHIFT.VehicleNamedBodyTopologyFrontier/2`, which proves exact retail BMW BODY indices for the four wheel and four spindle fields:

```text
slot       wheel BODY   spindle BODY
FL         3            1
FR         4            2
RL         7            5
RR         8            6
```

While Phase 702 was in CI, Process 1 PR #1188 merged
`SHIFT.BMWChassisBodyIdentityFrontier/1` and proved the central main/chassis BODY structurally from the retained retail suspension constraint topology:

```text
main/chassis BODY name   body
main/chassis BODY index  0
```

The proof does not rely on name plausibility: BODY 0 is the unique BODY incident to all twenty suspension BAR records across all four spindle families.

Phase 702 consumes both positive handoffs. It still keeps the vehicle `rear_axle` field at `+0x2e00` unresolved and keeps runtime vehicle selection fail-closed because active update-child -> `FUN_007615c0` vehicle solver-base continuity is not proven.

No original `SHIFT.exe` execution and no new runtime capture are used.

## Contract

```text
SHIFT.NativeBMWWheelSpindleBodyTopology/1
```

Native implementation:

```text
native_runtime/include/shift_bmw_wheel_spindle_body_topology.hpp
native_runtime/src/bmw_wheel_spindle_body_topology.cpp
```

The frozen retail topology carried by the native contract is:

```text
BODY count             11
wheel indices          [3, 4, 7, 8]
spindle indices        [1, 2, 5, 6]
main chassis index     0
slot order             FL, FR, RL, RR
rear axle index        unresolved
```

The eight wheel/spindle indices come from the exact Phase 404 archive-derived SDF order cross-checked by Process 1 #1184. The chassis index comes from Process 1 #1188's all-BAR endpoint proof against the same retail asset identity.

## Existing native relation-state consumer

The native constraint relation dispatcher already uses:

```text
VehicleConstraintBodyIdentityMap
```

with four wheel indices, four spindle indices and one rear-axle index. Before Phase 702 all nine values were generic caller inputs.

Phase 702 internalizes the eight proven wheel/spindle identities. A full relation-state map still requires:

```text
complete_bmw_vehicle_constraint_body_identity_map(...)
```

plus a separate `ProvenRearAxleBodyIndex` with `proven=true`.

The chassis BODY proof is intentionally independent of that relation-state completion. Process 1 #1188 explicitly proves that resolving `rear_axle` is not required to select the main/chassis BODY pose.

## Positive chassis handoff, negative runtime identity gate

Phase 702 now reports:

```text
main_chassis_body_selected = true
main_chassis_body_index = 0
update_child_to_vehicle_solver_base_continuity_proven = false
vehicle_body_selection_ready = false
phase698_positive_selection_admissible = false
```

The remaining blocker is not chassis semantics. It is runtime pointer continuity:

```text
*record + 0x340
  -> FUN_00794a30 update child
  -> ? same vehicle base
  -> FUN_007615c0 solver BODY fields
```

Until Process 1 proves that relationship, Phase 698/700 must not emit BODY 0 as the concrete runtime vehicle pose even though the retail chassis index itself is now known.

## Fail-closed rear-axle gate

`vehicle+0x2e00` remains a proven semantic `rear_axle` BODY-pointer field whose exact retail SDF BODY index is unknown.

Without a positive rear-axle proof, full `VehicleConstraintBodyIdentityMap` completion throws before the existing `FUN_00757d2c` dispatcher can consume the map. A supplied proven index must stay inside the exact eleven-BODY retail SDF domain.

Phase 702 deliberately does **not** impose an all-distinct rule: existing evidence does not prove that `rear_axle` must identify a BODY distinct from every wheel/spindle/chassis BODY.

The native regression uses synthetic `rear_axle=9` only to exercise the completion transport. It is not a retail identity claim.

## Relation-state identity reduction

For the existing `FUN_00757d2c` path:

```text
before:
  4 wheel indices
+ 4 spindle indices
+ rear axle index
= 9 caller-supplied identities

after Phase 702:
  8 BMW wheel/spindle identities source-backed/native
+ rear axle identity unresolved
```

Separately, the main/chassis BODY is now known as BODY 0 for future pose selection once update-child continuity closes.

Phase 702 does not schedule `FUN_00757d2c`, assign event timing, or claim that the relation-state dispatcher is already part of the deepest Phase 701 vehicle session.

## Python oracle

```text
src/physics/bmw_wheel_spindle_body_topology_runtime.py
tests/test_bmw_wheel_spindle_body_topology_runtime.py
```

The oracle verifies:

- exact eleven-BODY cardinality;
- exact four wheel and four spindle indices;
- proven main/chassis BODY index 0;
- chassis semantics come from retained constraint topology, not name plausibility;
- update-child -> solver-base continuity remains false;
- Phase 698 positive selection remains blocked;
- rear-axle completion fails without proof;
- out-of-range rear-axle proof fails;
- topology drift fails;
- no distinctness rule is invented.

## Native regression

```text
shift_runtime_bmw_wheel_spindle_body_topology_check
```

It independently verifies the exact arrays, chassis index 0 and the remaining runtime-continuity gate. It then exercises only the generic relation-map completion mechanism with a synthetic proven rear-axle index.

The emitted report keeps:

```text
rear_axle_body_index_ready = false
update_child_to_vehicle_solver_base_continuity_proven = false
vehicle_body_selection_ready = false
phase698_positive_selection_admissible = false
```

## Process 3 sync

Process 3 PR #1186 / Phase 643 provides one Silverstone + BMW neutral scene set and durable BMW renderer object identity. Process 1 #1188 now provides the physics-side semantic chassis BODY index.

The cross-domain join is still incomplete because runtime vehicle-object continuity and BODY-pose -> renderer/SVWT transform convention are not proven. Phase 702 therefore has no renderer, camera, SVWT or Vulkan side effect.

## Scheduling and provider boundaries

Phase 701 remains the deepest persistent explicit provider session. Phase 702 does not replace any of its nine Phase 699 external producer rows and does not attach either the relation dispatcher or outer update to `fixed_step()`.

```text
fixed_step_auto_schedule = false
vehicle_world_transform_proven = false
```

## Next blocker

The main pose-selection identity frontier is now singular:

1. Process 1: prove `*record+0x340 -> FUN_007615c0 vehicle base` continuity;
2. Process 2: once positive, feed the already-proven chassis BODY index 0 through Phase 698/700;
3. separately, Process 1 may still resolve `vehicle+0x2e00` for relation-state behavior;
4. after runtime vehicle identity and a proven BODY-pose -> SVWT convention exist, join Phase 700 pose output to Process 3's durable BMW renderer identity.
