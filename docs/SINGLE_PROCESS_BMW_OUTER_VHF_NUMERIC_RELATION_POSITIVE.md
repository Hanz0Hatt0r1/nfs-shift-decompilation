# Single process — BMW outer/VHF numeric relation positive

## BLOCKER

**Какой конкретный blocker первого playable Linux vertical slice снимает эта работа?**

It closes S2 `BMW-outer-VHF-numeric-relation-evaluation`. The semantic fixed-affine relation and first-primary-player-bootstrap `delta_local=(0,0,0)` were already positive, but the concrete retail BMW VHF Root matrix had not been retained.

## INPUT

The exact previously supplied Library bundle `bmwm3.zip` was materialized read-only and revalidated:

```text
bmwm3.zip SHA-256
6765b1420986773bce1dad19a03fefd00b8e9366c23d83935688e4fd467c44c9

BMW_M3_E36.bff SHA-256
c31d34a0a7cab04bcff693fa0cbda3400f50d690a9c8bb2521b2882fc2a68d70
```

The canonical BFF Type-2 entry is exactly:

```text
entry_index        1083
path               vehicles/bmw_m3_e36/bmw_m3_e36.vhf
compression_type   2
compressed_size    4914
uncompressed_size  88599
decoded_sha256     e08887d17d9e34e703a385260f41017fc19acbebc3405614b375e81766b4bd51
```

These identities exactly match the existing positive `SHIFT.BMWVehicleRenderModelResourceJoin/1`.

## RETAINED ROOT FRAME

The exact decoded VHF contains:

```xml
<NODE type="HIERARCHY" Name="Root" MatrixNumber="0" ... />
<MATRIX id="0"
        Offset="0.000000 0.000000 0.000000"
        Orientation="0.000000 0.000000 0.000000 1.000000" />
```

Matrix `0` has no parent. Therefore, under the already-established VHF column-vector hierarchy convention and exact row-vector transpose, the canonical Root matrix is source-backed identity:

```text
M_vhf_root_to_model = I4
```

This is **not** an inference from `MatrixNumber=0`; it follows from the explicit retail MATRIX record and parent chain.

The concrete retained root-frame instance is:

```text
evidence/bmw_vhf_hierarchy_root_frame_retail.json
SHIFT.BMWVHFHierarchyRootFrame/1
```

## OUTPUT

The merged PR #1342 evaluator consumes the retained Root frame plus:

```text
SHIFT.OuterVehicleBMWVHFRootRelation/1
SHIFT.BMWPrimaryPlayerFirstBootstrapRenderRootDelta/1
```

For the selected first bootstrap:

```text
delta_local = (0,0,0)
M_vhf_root_to_model = I4
M_outer_to_vhf_root = inverse(I4 * T(0,0,0)) = I4
```

Machine-readable positive output:

```text
evidence/bmw_outer_vhf_numeric_relation.json
SHIFT.BMWOuterVHFNumericRelation/1
```

New positive gate:

```text
outer_vehicle_root_to_VHF_relation_numeric_matrix_ready = true
```

Still fail-closed:

```text
BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready = false
BODY0_bind_frame_proof_ready = false
vehicle_world_transform_ready = false
```

Numeric identity is not promoted to semantic identity; the semantic contract remains setup-fixed affine.

## CONSUMER

S3 now composes the already-positive selected-session BODY0->outer numeric matrix with `M_outer_to_vhf_root=I4`, then publishes `SHIFT.BMWBody0BindFrameProof/1`.

## LIMITS

- No runtime capture or original-game execution.
- No matrix was guessed from MatrixNumber, naming, visuals, or test fixtures.
- The exact BMW resource bytes are not committed; only hashes, entry metadata, source record values, and derived proof output are retained.
- The result is scoped to the already-proven first primary-player bootstrap delta contract.

## TESTS

`tests/test_bmw_outer_vhf_numeric_relation_retail.py` re-runs the canonical PR #1342 evaluator over committed positive semantic/delta/root inputs and requires byte-for-JSON equality with the committed `SHIFT.BMWOuterVHFNumericRelation/1` output.

## NEXT_STEP

Compose selected BMW `BODY0->outer` with this exact `outer->VHF` matrix and publish positive `SHIFT.BMWBody0BindFrameProof/1` immediately.
