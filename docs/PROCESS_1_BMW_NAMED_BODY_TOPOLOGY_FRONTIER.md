# Process 1 — BMW named BODY topology frontier

## Playable-slice blocker reduced

Process 2 already carries persistent BODY origin/basis snapshots and Process 3
can materialize the regenerated renderer evidence into a prepared native scene.
The remaining transform blocker is no longer pose arithmetic: it is selecting the
retail BODY that represents the concrete vehicle/chassis.

This phase adds:

```text
SHIFT.VehicleNamedBodyTopologyFrontier/1
```

implemented by:

```text
tools/ghidra/build_vehicle_named_body_topology_frontier.py
```

It composes the merged `SHIFT.VehicleBodyIdentityFrontier/1`, the existing
`SHIFT.BodyPersistentStateABI/1`, and the exact
`SHIFT.BMWM3VehiclePhysicsResourceManifest/1`.

No original game execution and no new runtime capture are used.

## Proven vehicle BODY fields

Phase 633 and `FUN_007615c0` already establish the source BODY names behind the
vehicle solver setup, while raw disassembly/Phase 634 freezes the repeated
component geometry:

| Role | Vehicle field |
| --- | ---: |
| `fl_wheel` | `+0x820` |
| `fl_spindle` | `+0x824` |
| `fr_wheel` | `+0x12a0` |
| `fr_spindle` | `+0x12a4` |
| `rl_wheel` | `+0x1d20` |
| `rl_spindle` | `+0x1d24` |
| `rr_wheel` | `+0x27a0` |
| `rr_spindle` | `+0x27a4` |
| `rear_axle` | `+0x2e00` |

The four component blocks start at `vehicle+0x400` with stride `0xA80`; wheel
and spindle BODY fields are component-relative `+0x420/+0x424`.

These are nine named **field roles**. The phase does not invent a distinctness
rule for their runtime BODY indices.

## Exact BMW SDF cardinality

The committed retail manifest identifies:

```text
vehicles/physics/suspension/aarm_multilink.sdf
SHA-256 fe0b18e95e81f87d67076b70890965a0a1384a925bfd836aaf5aa705fc4781ed
BODY records 11
BODY runtime stride 0x170
```

Therefore the raw arithmetic difference is:

```text
11 retail BODY records - 9 named vehicle BODY field roles = 2
```

but **this is not yet promoted to an exact two-row candidate set**. Phase 634
intentionally did not prove that all named roles resolve to distinct BODY
indices, and the manifest stores counts/hashes rather than the exact BODY name
order.

The report therefore emits:

```text
arithmetic_difference = 2
arithmetic_difference_is_exact_residual_candidate_count = false
exact_residual_BODY_count = null
```

This removes a tempting but unsafe shortcut from the blocker graph.

## Optional exact-SDF closure

The same analyzer accepts:

```text
--sdf-source /path/to/aarm_multilink.sdf
```

Before using the file it requires the exact SHA-256 recorded in the BMW manifest.
It then reuses `src/physics/rigid_body_sdf_runtime.py` to recover the ordered
`BODY name=...` rows and the source-backed `0x170` lowering.

Only after the exact file proves every named vehicle BODY exactly once does the
contract emit the residual BODY rows and their runtime array indices. The exact
candidate cardinality can then become two without relying on subtraction alone.

Even at that point a residual name is not automatically declared the chassis.
A plausible name such as `body` would still need source/static semantics tying it
to the persistent vehicle world-pose source.

## Remaining joins

Two independent identity joins remain:

1. **main/chassis BODY semantic selection** — identify which exact SDF BODY owns
   the persistent vehicle pose used for the world transform;
2. **update-child -> vehicle solver base continuity** — join the merged
   `*record+0x340` update child to the vehicle base whose named BODY fields are
   populated by `FUN_007615c0`.

The finite static instruction worklist is:

```text
0x00713050  FUN_00713050 update batch
0x00794a30  first update child caller
0x007615c0  named vehicle solver BODY setup
```

The resource-side work item is the exact `aarm_multilink.sdf`; no new runtime
capture is required merely to obtain its BODY names/order.

## Downstream handoff

Until both joins are proven the report remains:

```text
persistent_BODY_pose_available = true
named_vehicle_BODY_fields_ready = true
main_chassis_BODY_selected = false
selected_BODY_index = null
vehicle_BODY_selection_ready = false
vehicle_world_transform_ready = false
renderer_vehicle_transform_transport_ready = false
```

Once a chassis BODY index is proven, Process 2 can select the already persistent
origin/basis snapshot and Process 3 can consume the resulting vehicle world
transform through the already prepared native-scene path.

## Fail-closed policy

The analyzer rejects:

- BMW archive identity drift;
- retail SDF path/hash/count/stride drift;
- component base/stride drift;
- wheel/spindle/rear-axle vehicle-field drift;
- upstream contracts that already claim a BODY selection;
- exact SDF files whose SHA-256 does not match the retail manifest;
- duplicated exact SDF BODY names;
- exact SDFs that do not contain every proven named vehicle BODY exactly once.

It never treats callgraph adjacency, offset similarity, cardinality subtraction,
or a human-plausible BODY name as chassis identity.
