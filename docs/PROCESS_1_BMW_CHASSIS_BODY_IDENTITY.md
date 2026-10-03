# Process 1 — BMW chassis BODY identity

## Playable-slice blocker reduced

The persistent BODY pose transport is already available through Process 2
Phases 695, 698 and 700. The remaining identity problem was previously split
into three items: the `rear_axle` field index, main/chassis BODY selection, and
update-child -> vehicle solver-base continuity.

This phase closes **main/chassis BODY selection** without using BODY-name
plausibility and proves that resolving `rear_axle` is not required for that
selection.

The new contract is:

```text
SHIFT.BMWChassisBodyIdentityFrontier/1
```

implemented by:

```text
tools/ghidra/build_bmw_chassis_body_identity_frontier.py
```

No original game execution and no new runtime capture are used.

## Exact retail identity

The proof requires the same retail identities already frozen by Phase 404 and
Phase 405:

```text
archive      BMW_M3_E36.bff
archive SHA  c31d34a0a7cab04bcff693fa0cbda3400f50d690a9c8bb2521b2882fc2a68d70
SDF          vehicles/physics/suspension/aarm_multilink.sdf
SDF SHA      fe0b18e95e81f87d67076b70890965a0a1384a925bfd836aaf5aa705fc4781ed
BODY count   11
BAR count    20
```

Phase 404 supplies the exact BODY order, including:

```text
0   body
1   fl_spindle
2   fr_spindle
...
9   fuel_tank
10  driver_head
```

Phase 405 records the same exact archive/SDF identity as
`source-backed-real-asset-topology` and freezes the recovered solver ordering
signature:

```text
FUN_007b1b60
initial cost      17516
final cost        17296
improvements      2
passes            2
final order tail  [25, 24, 27, 26]
```

## Retained Phase 405 constraint topology

The Phase 405 regression retained the exact real-asset topology reconstruction
used to obtain that solver domain. Process 1 now stores the identity-relevant
part explicitly in:

```text
evidence/bmw_m3_e36_chassis_body_topology_process1.json
```

The four wheel/spindle JOINT&Hinge pairs are:

```text
fl_wheel <-> fl_spindle
fr_wheel <-> fr_spindle
rl_wheel <-> rl_spindle
rr_wheel <-> rr_spindle
```

All twenty suspension BAR records share one endpoint, `body`, with five BARs to
each of the four spindle BODYs:

```text
body <-> fl_spindle  x5
body <-> fr_spindle  x5
body <-> rl_spindle  x5
body <-> rr_spindle  x5
```

Therefore BAR endpoint degree is:

```text
body        20
fl_spindle   5
fr_spindle   5
rl_spindle   5
rr_spindle   5
all others   0
```

`body` is the **unique BODY incident to every suspension BAR**. This is a
structural main-suspension/chassis role, independent of the human plausibility
of its name.

Joining that role back to the exact Phase 404 BODY order selects:

```text
main/chassis BODY name   body
main/chassis BODY index  0
```

## Fail-closed checks

The builder rejects:

- Phase 404 archive or SDF hash drift;
- Phase 405 archive/SDF identity or provenance drift;
- Phase 405 BODY, JOINT&Hinge, BAR or scalar-count drift;
- Phase 405 ordering-signature drift;
- retained Phase 405 reconstruction commit drift;
- joint endpoint or axis drift against Phase 404;
- BAR total/target-family/degree drift;
- a non-unique all-BAR endpoint;
- disagreement between selected BODY name and exact Phase 404 index.

The proof explicitly records:

```text
body_name_alone_proves_chassis_semantics = false
constraint_topology_proves_main_suspension_BODY = true
```

## `rear_axle` is no longer on the pose-selection critical path

`vehicle+0x2e00` remains a proven semantic `rear_axle` BODY-pointer field whose
exact SDF index is unknown. That identity may still matter for relation-state
mutation and other vehicle behavior, but it is not needed to select the central
main/chassis BODY pose.

The frontier therefore records this as a residual noncritical unknown instead
of a blocker for Phase 698/700 pose selection.

## Remaining direct identity blocker

The selected BODY index is now known, but Process 1 still has not proven that
the active update child is the same vehicle object whose solver BODY fields are
populated by `FUN_007615c0`:

```text
0x00713050  update batch / *record+0x340 producer
0x00794a30  update-child consumer
0x007615c0  vehicle solver BODY-field setup
```

Until that pointer continuity is proven, the handoff remains deliberately:

```text
main_chassis_BODY_selected = true
main_chassis_BODY_index = 0
update_child_to_vehicle_solver_base_continuity_proven = false
vehicle_BODY_selection_ready = false
phase698_positive_selection_admissible = false
```

The next Process 1 task is therefore finite and singular: prove
`*record+0x340 -> FUN_007615c0 vehicle base` continuity. Once positive, Process
2 can emit the already-supported proven BODY 0 pose through Phase 698/700.
