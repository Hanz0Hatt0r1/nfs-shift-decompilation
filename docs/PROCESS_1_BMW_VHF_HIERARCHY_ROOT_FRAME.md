# Process 1 — exact BMW VHF HIERARCHY-root frame

## BLOCKER

**Какой конкретный blocker первого playable Linux vertical slice снимает эта работа?**

`SHIFT.BMWBody0BindFrameProof/1` is still blocked by the unresolved outer
Vehicle-root -> exact BMW VHF vehicle-root relation.

The positive `SHIFT.BMWVehicleRenderModelResourceJoin/1` already fixes the BMW
Vehicle Render Model to the unique retail resource:

```text
vehicles/bmw_m3_e36/bmw_m3_e36.vhf
```

but that contract intentionally stops at resource identity and only records that
the decoded VHF exposes a `HIERARCHY` root.  The next value/provenance join must
not compare `FUN_00795d60` values to a prose label such as `Root`; it needs the
exact source-backed VHF root node and affine frame.

## INPUT

```text
SHIFT.BMWVehicleRenderModelResourceJoin/1
+ exact BMW_M3_E36.bff admitted by that contract
```

The builder revalidates:

- retail `SHIFT.exe` identity when present in the resource join;
- exact canonical logical VHF path;
- primary archive name and SHA-256;
- unique archive entry and entry index;
- exact decoded VHF SHA-256;
- decoded `<CAR Name="BMW_M3_E36">` identity.

## OUTPUT

`tools/ghidra/build_bmw_vhf_hierarchy_root_frame.py` emits:

```text
SHIFT.BMWVHFHierarchyRootFrame/1
```

A positive result proves all of the following from the exact decoded VHF:

```text
unique direct NODE[type=HIERARCHY]
node Name == Root
exact MatrixNumber
exact referenced MATRIX record
exact parent chain
Offset / Orientation for every matrix in that chain
local 4x4 matrix
resolved world 4x4 matrix
exact row-vector transpose used by the existing VHF scene path
```

The matrix evaluator uses the same source convention already used by the VHF
scene adapter:

```text
VHF matrix: row-major storage, column-vector transform
world = parent_world * local
D3D/SVWT row-vector representation = exact transpose(world)
```

Unlike the preview adapter, this proof does **not** synthesize an identity matrix
for a missing `MATRIX` record.  The root frame is positive only when every matrix
in the root parent chain is explicitly present in the retail VHF payload.

Invocation:

```bash
python3 tools/ghidra/build_bmw_vhf_hierarchy_root_frame.py \
  evidence/process1_bmw_vehicle_render_model_resource_join.json \
  /path/to/BMW_M3_E36.bff \
  --json-out out/bmw_vhf_hierarchy_root_frame.json
```

## CONSUMER

The immediate Process 1 consumer is the already-bounded producer proof:

```text
SHIFT.OuterVehicleRenderRootDeltaProvenance/1
        |
        | exact +0x19c/+0x1a0/+0x1a4 value roots
        v
SHIFT.BMWVHFHierarchyRootFrame/1
        |
        v
outer Vehicle-root == VHF vehicle-root
OR exact fixed affine delta
```

The later join must use value/resource provenance to establish that relation. It
must not infer it from an identity-valued VHF root matrix, equal numbers,
callgraph adjacency, helper names or visual agreement.

## Gates

This contract may make only these new resource-side gates positive:

```text
canonical_BMW_VHF_hierarchy_root_frame_ready  = true
canonical_BMW_VHF_hierarchy_root_matrix_ready = true
```

It deliberately keeps these false:

```text
outer_vehicle_root_to_VHF_vehicle_root_ready         = false
outer_vehicle_root_to_VHF_fixed_affine_delta_ready   = false
BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready = false
BODY0_bind_frame_proof_ready                         = false
vehicle_world_transform_ready                        = false
```

No runtime capture or original-game execution is required.
