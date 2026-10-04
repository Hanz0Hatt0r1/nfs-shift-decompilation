# Process 1 — positive BMW BODY0 resource values

## Playable-slice blocker removed

The retail BMW construction proof previously stopped at data availability: the
repository knew the exact `aarm_multilink.sdf` identity and the machine path
from SDF `BODY.pos/ori` into persistent BODY origin/basis, but the exact BODY0
numeric values were not retained as committed derived evidence.

The exact retail `BMW_M3_E36.bff` was re-observed through the already-supported
BFF Type-2 XMem/LZX extraction path. No retail bytes are committed by this
phase.

Exact admitted identities:

```text
BMW_M3_E36.bff SHA-256
c31d34a0a7cab04bcff693fa0cbda3400f50d690a9c8bb2521b2882fc2a68d70

entry 1091
vehicles/physics/suspension/aarm_multilink.sdf
compression type 2
compressed size 1110
uncompressed size 5056
decoded SHA-256
fe0b18e95e81f87d67076b70890965a0a1384a925bfd836aaf5aa705fc4781ed
```

The exact decoded chassis BODY is:

```text
BODY index = 0
BODY name  = body
BODY0.pos  = (0.0, 0.0, 0.0)
BODY0.ori  = (0.0, 0.0, 0.0)
```

Because the already-proven retail `FUN_007b00a0` basis builder has an exact
zero-orientation identity shortcut, the construction-side matrix is now exact:

```text
BODY0-local -> SDF model construction frame

[ 1 0 0 0 ]
[ 0 1 0 0 ]
[ 0 0 1 0 ]
[ 0 0 0 1 ]
```

This is a row-vector affine matrix, matching the existing construction
continuity contract.

## Machine-readable evidence

Exact resource observation:

```text
evidence/bmw_body0_bind_resource_materialization.json
SHIFT.BMWBody0BindResourceMaterialization/1
```

Promoted construction continuity:

```text
evidence/bmw_body0_construction_bind_continuity_resource_join.json
SHIFT.BMWBody0ConstructionBindContinuity/1
```

Promotion tool:

```text
tools/ghidra/promote_bmw_body0_construction_bind_resource.py
```

The promotion tool consumes only committed machine-readable evidence. It
validates archive SHA, SDF path/SHA/entry/size, BODY index/name/count, finite
numeric vectors and consistency of the exact-zero flags. It then removes only
the resource-data blocker.

## Positive handoff

The following are now positive:

```text
BODY_descriptor_pos_ori_semantics_ready       = true
construction_origin_continuity_ready          = true
construction_basis_continuity_ready           = true
BODY0_resource_pos_ori_values_ready            = true
BODY0_local_to_SDF_model_bind_pose_ready       = true
```

The following deliberately remain false:

```text
SDF_model_to_VHF_vehicle_root_frame_relation_ready = false
BODY0_bind_frame_proof_ready                       = false
vehicle_world_transform_ready                       = false
```

Zero BODY0 pose does not prove that the SDF model parent frame equals the VHF
vehicle-root/assembly frame.

## Next blocker

The transform path no longer needs more BODY construction-writer discovery or
resource recovery. The shortest remaining Process 1 path is the existing
`offset33b`/outer-Vehicle static proof chain:

```text
BODY0-local -> SDF model                 exact identity
        |
        v
BODY0-local -> outer Vehicle root        symbolic translation = -offset33b
        |
        v
BMW numeric offset33b                    still blocked
        |
        v
outer Vehicle root -> VHF vehicle root  still blocked
        |
        v
SHIFT.BMWBody0BindFrameProof/1
```

Continue with `SHIFT.BMWOffset33bReducedStaticProofBundle/1`; do not reopen the
closed BODY construction or anonymous outer-Vehicle owner searches.

## Scope

This phase does not commit `BMW_M3_E36.bff` or decoded SDF bytes, execute the
original game, request a runtime capture, change native physics, change Vulkan
rendering, or infer SDF/VHF parent-frame equality from zero resource values.
