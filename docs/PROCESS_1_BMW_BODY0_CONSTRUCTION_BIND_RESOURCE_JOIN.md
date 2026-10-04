# Process 1 — BMW BODY0 construction-bind resource join

## Playable-slice blocker reduced

The retail BMW world-transform path already had static proof that SDF `BODY.pos`
and `BODY.ori` feed the persistent BODY origin and basis through
`FUN_007b3670 -> FUN_007bbb10 -> FUN_007b00a0`. The remaining construction-side
blocker was data availability: exact BMW `BODY[0].pos/ori` values were not
committed in a byte-free form usable by CI.

The exact retail `BMW_M3_E36.bff` was recovered from the connected game-resource
store and admitted by the already frozen hashes:

```text
BMW_M3_E36.bff SHA-256
c31d34a0a7cab04bcff693fa0cbda3400f50d690a9c8bb2521b2882fc2a68d70

vehicles/physics/suspension/aarm_multilink.sdf SHA-256
fe0b18e95e81f87d67076b70890965a0a1384a925bfd836aaf5aa705fc4781ed
```

The exact archive entry also matches the Phase 404 intake contract:

```text
entry index       1091
compression type  2
compressed size   1110
uncompressed size 5056
BODY count        11
BODY[0]            body
```

No BFF or SDF bytes are committed by this stage. Only hash-bound derived
metadata is stored in:

```text
evidence/bmw_m3_e36_body0_bind_resource_values.json
```

with format:

```text
SHIFT.BMWBody0BindResourceValues/1
```

## Exact BODY0 values

The hash-admitted retail SDF gives:

```text
BODY[0].name = body
BODY[0].pos  = (0.0, 0.0, 0.0)
BODY[0].ori  = (0.0, 0.0, 0.0)
```

The existing `SHIFT.BMWBody0ConstructionBindContinuity/1` proof already states:

```text
BODY.pos -> persistent BODY origin
BODY.ori -> FUN_007b00a0 -> persistent BODY 3x3 basis
```

Because both the translation and orientation resource values are literal exact
zero, the existing zero-orientation shortcut is applicable without host
trigonometric evaluation. Therefore:

```text
BODY0-local -> SDF-model construction frame
```

is the exact D3D row-vector affine identity matrix:

```text
1 0 0 0
0 1 0 0
0 0 1 0
0 0 0 1
```

This is a derived result, not an assumed identity.

## Machine-readable join

Tool:

```text
tools/ghidra/build_bmw_body0_construction_bind_resource_join.py
```

Output:

```text
SHIFT.BMWBody0ConstructionBindResourceJoin/1
```

The tool first reruns the existing static construction continuity validation
against the exact retail function fingerprints and required direct callsites.
It then validates the committed resource-values evidence against the Phase 404
intake and fixed retail archive/resource identity. The matrix is recomputed
from the admitted scalar values; a matrix stored in evidence is never trusted.

Run:

```bash
python3 tools/ghidra/build_bmw_body0_construction_bind_resource_join.py \
  out/shift_ghidra_database \
  evidence/bmw_m3_e36_physics_intake_phase404.json \
  --json-out out/bmw_body0_construction_bind_resource_join.json
```

No original game execution, runtime capture, BFF bytes or decoded SDF bytes are
required by this CI path.

## New proof state

The construction-side portion is now positive:

```text
BODY_descriptor_pos_ori_semantics_ready              = true
construction_origin_continuity_ready                 = true
construction_basis_continuity_ready                  = true
BODY0_resource_pos_ori_values_ready                  = true
BODY0_local_to_SDF_model_bind_pose_ready             = true
```

The final frame join remains deliberately false:

```text
SDF_model_to_VHF_vehicle_root_frame_relation_ready   = false
BODY0_bind_frame_proof_ready                         = false
vehicle_world_transform_ready                        = false
```

## Remaining blocker

The shortest remaining transform-semantic blocker is now exactly:

```text
SDF model construction frame
        ->
VHF vehicle-root / assembly frame
```

Zero BODY0 local pose is not evidence that those two parent frames are equal.
The next Process 1 work must prove that relation from static owner/assembly/frame
provenance rather than infer it from names, zero values, or the previously
observed `+0x340` car-body child signature.
