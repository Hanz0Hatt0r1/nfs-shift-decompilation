# Phase 702 — BMW wheel/spindle BODY topology handoff

## Playable-slice blocker reduced

Process 1 PR #1184 / `SHIFT.VehicleNamedBodyTopologyFrontier/2` closes eight
retail BMW BODY identities that were still represented as manually supplied
indices by the existing native vehicle relation-state dispatcher:

```text
slot       wheel BODY   spindle BODY
FL         3            1
FR         4            2
RL         7            5
RR         8            6
```

The same Process 1 result explicitly keeps the vehicle `rear_axle` field at
`+0x2e00` unresolved and does not select the main/chassis BODY.

Phase 702 moves only the eight proven identities into the native runtime ABI. It
does not guess the ninth index, a chassis BODY, or any world-transform mapping.

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

The frozen retail topology is:

```text
BODY count       11
wheel indices    [3, 4, 7, 8]
spindle indices  [1, 2, 5, 6]
slot order       FL, FR, RL, RR
```

These indices come directly from the exact Phase 404 archive-derived SDF order
that Process 1 #1184 cross-checked against the retail BMW physics manifest.

## Existing native consumer

The native constraint relation dispatcher already uses:

```text
VehicleConstraintBodyIdentityMap
```

with four wheel indices, four spindle indices and one rear-axle index. Before
Phase 702 all nine values were generic caller inputs.

Phase 702 introduces `BmwWheelSpindleBodyTopology` so the eight proven values no
longer need to be supplied independently. The topology still reports:

```text
rear_axle_body_index_ready = false
main_chassis_body_selected = false
```

A full `VehicleConstraintBodyIdentityMap` can only be produced through:

```text
complete_bmw_vehicle_constraint_body_identity_map(...)
```

and that function requires a separate `ProvenRearAxleBodyIndex` with
`proven=true`.

## Fail-closed rear-axle gate

Without a positive rear-axle proof, completion throws before any
`FUN_00757d2c` dispatcher can consume the map.

A supplied proven index must also stay inside the exact eleven-BODY retail SDF
domain. Phase 702 deliberately does **not** impose an all-distinct rule: Phase
634 did not prove that `rear_axle` must identify a BODY distinct from every
wheel/spindle BODY.

The native regression uses a synthetic positive `rear_axle=0` solely to test the
completion transport. It is explicitly not a retail identity claim.

## Chassis identity remains blocked

The three exact SDF rows not consumed by the eight name joins remain:

```text
0   body
9   fuel_tank
10  driver_head
```

Phase 702 does not infer that SDF name `body` is the main/chassis BODY. Thus:

```text
main_chassis_body_selected = false
phase698_positive_selection_admissible = false
```

Phase 698/700 persistent vehicle pose selection remains fail-closed.

## Relation-state impact

This phase narrows the identity surface of the existing `FUN_00757d2c` path:

```text
before:
  4 wheel indices
+ 4 spindle indices
+ rear axle index
= 9 caller-supplied identities

after Phase 702:
  8 BMW wheel/spindle identities native/source-backed
+ rear axle identity unresolved
```

It does not schedule `FUN_00757d2c`, assign event timing, or claim that the
relation-state dispatcher is already part of the deepest Phase 701 vehicle
session.

## Python oracle

```text
src/physics/bmw_wheel_spindle_body_topology_runtime.py
tests/test_bmw_wheel_spindle_body_topology_runtime.py
```

The oracle verifies:

- exact eleven-BODY cardinality;
- exact four wheel and four spindle indices;
- rear-axle completion fails without proof;
- out-of-range rear-axle proof fails;
- topology drift fails;
- no distinctness/chassis inference is introduced.

## Native regression

```text
shift_runtime_bmw_wheel_spindle_body_topology_check
```

It independently verifies the exact arrays and negative gates, then exercises
only the generic completion mechanism with a synthetic proven rear-axle index.
The emitted report keeps the retail rear-axle/chassis claims false.

## Process 3 sync

Process 3 PR #1186 / Phase 643 provides one Silverstone + BMW neutral scene set
and durable BMW renderer object identity. That does not identify a physics
chassis BODY and does not make any of the eight wheel/spindle indices a renderer
vehicle transform.

Phase 702 therefore has no renderer, camera, SVWT or Vulkan side effect.

## Scheduling and provider boundaries

Phase 701 remains the deepest persistent explicit provider session. Phase 702
does not replace any of its nine Phase 699 external producer rows and does not
attach either the relation dispatcher or outer update to `fixed_step()`.

```text
fixed_step_auto_schedule = false
vehicle_world_transform_proven = false
```

## Next blocker

The remaining direct identity work is now smaller:

1. Process 1: prove `vehicle+0x2e00` -> exact retail SDF BODY index;
2. Process 1: prove the main/chassis BODY and update-child -> vehicle solver-base
   continuity;
3. Process 2: consume the first positive proof through the existing typed gates;
4. only after chassis selection and a proven BODY-pose -> SVWT convention, join
   Phase 700 pose output to the Process 3 renderer vehicle identity.
