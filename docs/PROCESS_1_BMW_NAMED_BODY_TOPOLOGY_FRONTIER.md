# Process 1 — BMW named BODY topology frontier

## Playable-slice blocker reduced

Process 2 Phase 698 can select a persistent BODY pose only after Process 1
supplies a proven BODY index. Process 3 already has a prepared native-scene
handoff. The remaining transform blocker is therefore identity, not pose decode.

The current contract is:

```text
SHIFT.VehicleNamedBodyTopologyFrontier/2
```

implemented by:

```text
tools/ghidra/build_vehicle_named_body_topology_frontier.py
```

Version 2 supersedes v1 because existing Phase 404 archive-derived evidence
contains the exact retail SDF BODY order and disproves one v1 assumption.

No original game execution and no new runtime capture are used.

## Exact retail SDF order was already committed

`evidence/bmw_m3_e36_physics_intake_phase404.json` was decoded from the
user-supplied `BMW_M3_E36.bff`. It records the same SDF identity as the current
vehicle physics manifest:

```text
path       vehicles/physics/suspension/aarm_multilink.sdf
entry      1091
size       5056 bytes
SHA-256    fe0b18e95e81f87d67076b70890965a0a1384a925bfd836aaf5aa705fc4781ed
BODY count 11
```

and the exact archive-derived BODY order:

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

The contract cross-checks the Phase 404 path, entry index, decoded SHA-256,
uncompressed size and BODY count against
`SHIFT.BMWM3VehiclePhysicsResourceManifest/1` before accepting this name order.

## Correction to v1: `rear_axle` is a vehicle field role, not an SDF name

Phase 633 / `FUN_007615c0` proves the vehicle solver BODY fields:

| Vehicle field role | Vehicle field | Exact retail SDF name/index |
| --- | ---: | --- |
| `fl_wheel` | `+0x820` | `fl_wheel`, 3 |
| `fl_spindle` | `+0x824` | `fl_spindle`, 1 |
| `fr_wheel` | `+0x12a0` | `fr_wheel`, 4 |
| `fr_spindle` | `+0x12a4` | `fr_spindle`, 2 |
| `rl_wheel` | `+0x1d20` | `rl_wheel`, 7 |
| `rl_spindle` | `+0x1d24` | `rl_spindle`, 5 |
| `rr_wheel` | `+0x27a0` | `rr_wheel`, 8 |
| `rr_spindle` | `+0x27a4` | `rr_spindle`, 6 |
| `rear_axle` | `+0x2e00` | **unresolved** |

The exact retail SDF has no `name=rear_axle` record. Therefore v1's optional
SDF join incorrectly required a `rear_axle` name that cannot exist in the
hash-matched retail file.

Version 2 fixes this by distinguishing:

```text
source/vehicle semantic BODY field role
!=
exact SDF name string
```

for `vehicle+0x2e00`.

## Exact name join now closed for eight fields

The eight wheel/spindle fields map directly to exact Phase 404 BODY indices.
No ZIP extraction is required to establish these indices; the committed evidence
already carries the archive-derived order with the exact decoded SDF hash.

The exact SDF rows not consumed by those eight direct name joins are:

```text
0   body
9   fuel_tank
10  driver_head
```

These are recorded as **non-wheel/spindle residual rows**, not automatically as
three chassis candidates. A BODY name by itself is not enough to promote chassis
or renderer identity.

The `rear_axle` field may still require independent source/machine pointer
provenance to determine which exact SDF BODY it references. Phase 634 deliberately
does not invent a distinctness rule for named BODY indices.

## Optional raw-SDF cross-check

The CLI still accepts:

```text
--sdf-source /path/to/aarm_multilink.sdf
```

but raw SDF bytes are no longer required for baseline name/order recovery. When
provided, the tool checks the exact manifest SHA-256, parses the source with the
existing SDF runtime parser and requires its ordered BODY names to match Phase
404 byte-derived evidence exactly.

## Remaining direct blockers

### 1. `rear_axle` field role -> exact SDF BODY index

Trace value production in `FUN_007615c0` for:

```text
vehicle + 0x2e00
```

to one exact BODY pointer/index without treating the semantic label as a file
name.

### 2. Main/chassis BODY semantic selection

The exact non-wheel/spindle rows are now known, but Process 1 still needs static
proof of which BODY supplies the persistent vehicle/chassis world pose. The
string `body` is a strong human hint, not sufficient evidence by itself.

### 3. Update child -> vehicle solver base continuity

PR #1176 proves the active update child as:

```text
*record + 0x340
```

but does not prove that this pointer is the same vehicle base used by
`FUN_007615c0`. The finite instruction worklist remains:

```text
0x00713050  update batch / *record+0x340 producer
0x00794a30  update-child consumer
0x007615c0  vehicle solver BODY-field setup
```

## Phase 698 handoff

The contract deliberately keeps:

```text
persistent_BODY_pose_available = true
exact_sdf_BODY_name_order_ready = true
wheel_spindle_BODY_indices_ready = true
rear_axle_BODY_index_ready = false
main_chassis_BODY_selected = false
selected_BODY_index = null
vehicle_BODY_selection_ready = false
phase698_positive_selection_admissible = false
```

Only after the chassis identity and update-child continuity are proven should the
positive `SHIFT.VehicleBodyIdentityFrontier/1` fields required by Phase 698 be
emitted.

## Fail-closed policy

Version 2 rejects:

- BMW manifest SDF path/hash/count/stride drift;
- Phase 404 archive/path/index/hash/size/count drift;
- duplicate Phase 404 BODY names;
- component or vehicle BODY-field topology drift;
- absence of any of the eight proven wheel/spindle SDF names;
- any future exact retail `rear_axle` name appearing without a re-audit of the
  Phase 633 semantic role;
- raw SDF content whose SHA-256 or BODY order differs from Phase 404;
- upstream preselection of a vehicle BODY.

It never promotes offset similarity, a semantic field label, an SDF name, or a
cardinality subtraction into chassis identity.
