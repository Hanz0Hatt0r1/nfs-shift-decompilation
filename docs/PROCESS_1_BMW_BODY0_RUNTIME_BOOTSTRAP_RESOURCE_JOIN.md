# Process 1 — BMW BODY0 resource join from unified runtime bootstrap

## Playable-slice blocker removed

Process 3 now persists every exact typed BMW physics resource and exposes the
selected decoded SDF through:

```text
SHIFT.OfflineRuntimeBootstrap/1
  artifacts.vehicle_sdf
```

Before this join, Process 1 still needed the original `BMW_M3_E36.bff` again to
run `tools/materialize_bmw_body0_bind_resource.py`, even though the unified
resource bootstrap had already materialized and hash-admitted the exact decoded
`vehicles/physics/suspension/aarm_multilink.sdf`.

That duplicate extraction/data-availability edge is removed. The existing
`SHIFT.BMWBody0BindResourceMaterialization/1` can now consume the unified
bootstrap directly and produce exact BODY0 `pos/ori` from the already-admitted
SDF bytes.

## Command

After one successful resource-driven runtime bootstrap:

```bash
python3 tools/materialize_bmw_body0_bind_resource.py \
  --runtime-bootstrap out/runtime/runtime_bootstrap.json \
  --json-out out/bmw_body0_bind_resource.json
```

The original BFF path remains supported:

```bash
python3 tools/materialize_bmw_body0_bind_resource.py \
  /path/to/BMW_M3_E36.bff \
  --sdf-out out/vehicles/physics/suspension/aarm_multilink.sdf \
  --json-out out/bmw_body0_bind_resource.json
```

Exactly one source must be selected.

## Fail-closed join

The runtime-bootstrap path accepts the SDF only when all of these remain true:

```text
runtime bootstrap format
  = SHIFT.OfflineRuntimeBootstrap/1

offline_build_ready
  = true

vehicle
  = BMW_M3_E36

readiness.retail_archive_identity_ready
  = true

readiness.vehicle_physics_materialized_resources_ready
  = true
```

The referenced `vehicle_physics_manifest` must also be
`SHIFT.VehiclePhysicsResourceManifest/1`, ready, have no blocking reasons and
report `materialized_resources_ready=true`.

Its SDF row must match exactly:

```text
path
  = vehicles/physics/suspension/aarm_multilink.sdf

decoded_sha256
  = fe0b18e95e81f87d67076b70890965a0a1384a925bfd836aaf5aa705fc4781ed

materialized_sha256
  = fe0b18e95e81f87d67076b70890965a0a1384a925bfd836aaf5aa705fc4781ed

materialization_source
  = SHIFT.TypedResourceClosure/1
```

`runtime_bootstrap.artifacts.vehicle_sdf` and the manifest's
`entries.sdf.materialized_path` must resolve to the same file. The current bytes
are re-hashed before parsing and must still match the exact decoded SHA-256.
This protects Process 1 from stale, replaced or path-confused materializations.

No BFF archive is re-opened in this mode and Process 1 does not rederive Process
3's typed-resource admission semantics.

## BODY0 output

After exact identity validation, the existing strict SDF parser remains the only
BODY parser. BODY ordering must still be the Phase 404 retail ordering with:

```text
BODY count = 11
BODY[0].name = body
```

The output retains the existing contract and gates:

```text
SHIFT.BMWBody0BindResourceMaterialization/1

BODY0_resource_pos_ori_values_ready = true
construction_bind_continuity_input_ready = true
BODY0_local_to_SDF_model_bind_pose_ready = false
BODY0_bind_frame_proof_ready = false
vehicle_world_transform_ready = false
```

The legacy negative
`SDF_model_to_VHF_vehicle_root_frame_relation_ready=false` field is retained for
`/1` compatibility. The current, more precise symbolic proof also exposes
`outer_vehicle_root_to_VHF_vehicle_root_ready=false`.

## Remaining world-transform blockers

Process 1 PR #1232 already proves the symbolic BODY0-local -> outer Vehicle-root
relation:

```text
rotation = identity
translation = -offset33b
```

Therefore successful BODY0 resource materialization no longer leaves a broad
resource/data blocker. The remaining direct bind/world-transform work is:

1. exact BMW numeric `HDVehicle+0x33b0/+0x33b8/+0x33c0` (`offset33b`) values;
2. outer `Vehicle` root -> VHF vehicle-root static/source-backed relation.

No identity translation, VHF equality, runtime scheduling or vehicle-world
transform is claimed by this resource join.
