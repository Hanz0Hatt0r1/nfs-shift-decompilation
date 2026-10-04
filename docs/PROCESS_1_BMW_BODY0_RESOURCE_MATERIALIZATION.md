# Process 1 — BMW BODY0 resource materialization

## Playable-slice blocker reduced

`SHIFT.BMWBody0ConstructionBindContinuity/1` reduced the retail vehicle world
transform blocker to two finite joins.  The first is purely data availability:
recover the already-measured retail
`vehicles/physics/suspension/aarm_multilink.sdf` bytes and expose exact
`BODY[0].pos` / `BODY[0].ori` to the construction-bind proof.

This stage adds a one-command, fail-closed materializer:

```text
tools/materialize_bmw_body0_bind_resource.py
```

with machine-readable output:

```text
SHIFT.BMWBody0BindResourceMaterialization/1
```

It deliberately does not solve the remaining SDF-model -> VHF vehicle-root
frame relation.

## Reused evidence and decoder

No new BFF or compression semantics are introduced.  The tool reuses the
existing exact-retail extraction boundary from:

```text
tools/verify_bmw_m3_e36_solver_domain.py
  -> extract_target_sdf()
  -> shift_importer_v3_reference.BFF
  -> existing Type-2 XMem/LZX decoder
```

The extraction boundary already requires:

```text
BMW_M3_E36.bff SHA-256
  c31d34a0a7cab04bcff693fa0cbda3400f50d690a9c8bb2521b2882fc2a68d70

vehicles/physics/suspension/aarm_multilink.sdf SHA-256
  fe0b18e95e81f87d67076b70890965a0a1384a925bfd836aaf5aa705fc4781ed
```

The new materializer then joins the decoded bytes back to the checked-in
`SHIFT.BMWM3PhysicsIntakeEvidence/1` contract and additionally requires the exact
Phase 404 entry identity:

```text
entry index       1091
compression type  2
compressed size   1110
uncompressed size 5056
BODY count        11
BODY[0] name      body
```

Any drift fails closed.

## BODY0 output

After exact resource admission, the existing source-backed
`rigid_body_sdf_runtime.parse_sdf(..., strict=True)` parser is used.  The tool
requires the full known BMW BODY order and reports:

```text
body0.pos
body0.ori
body0.ori_is_exact_zero
zero_orientation_identity_shortcut_eligible
```

The zero-orientation flag is only an input to the already proven construction
continuity pass.  This materializer itself does not evaluate or invent a basis.

When `--sdf-out` is provided, the exact verified decoded bytes are written so
they can be passed directly to:

```text
tools/ghidra/build_bmw_body0_construction_bind_continuity.py --sdf ...
```

## Handoff boundary

A successful report may assert only:

```text
BODY0_resource_pos_ori_values_ready        = true
construction_bind_continuity_input_ready   = true
```

It intentionally keeps:

```text
BODY0_local_to_SDF_model_bind_pose_ready             = false
SDF_model_to_VHF_vehicle_root_frame_relation_ready   = false
BODY0_bind_frame_proof_ready                         = false
vehicle_world_transform_ready                        = false
```

The first false value becomes eligible for promotion only when the existing
construction continuity proof consumes the materialized SDF.  The final two
remain blocked on the independent SDF-model -> VHF vehicle-root frame relation.

## Run

```bash
python3 tools/materialize_bmw_body0_bind_resource.py \
  /path/to/BMW_M3_E36.bff \
  --sdf-out out/vehicles/physics/suspension/aarm_multilink.sdf \
  --json-out out/bmw_body0_bind_resource.json
```

Then feed the exact SDF to the existing proof:

```bash
python3 tools/ghidra/build_bmw_body0_construction_bind_continuity.py \
  out/shift_ghidra_database \
  evidence/bmw_m3_e36_physics_intake_phase404.json \
  --sdf out/vehicles/physics/suspension/aarm_multilink.sdf \
  --json-out out/bmw_body0_construction_bind_continuity.json
```

## Regression coverage

`tests/test_materialize_bmw_body0_bind_resource.py` freezes:

- exact Phase 404 intake identity;
- exact decoded entry provenance;
- full BMW BODY order;
- BODY0 numeric `pos`/`ori` extraction;
- exact-zero orientation eligibility;
- non-zero orientation without basis invention;
- fail-closed metadata/body-order drift;
- continued false final bind/world-transform claims.
