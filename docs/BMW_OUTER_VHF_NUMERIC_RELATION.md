# BMW outer Vehicle -> VHF numeric relation

## BLOCKER

**Какой конкретный blocker первого playable Linux vertical slice снимает эта работа?**

This stage closes S2: evaluate the already-positive setup-fixed semantic relation
for the selected first native Silverstone + BMW primary-player bootstrap and
materialize a finite numeric `M_outer_to_vhf_root`.

## INPUT

Positive contracts:

```text
SHIFT.OuterVehicleBMWVHFRootRelation/1
SHIFT.BMWPrimaryPlayerFirstBootstrapRenderRootDelta/1
SHIFT.BMWVehicleRenderModelResourceJoin/1
```

Exact retail archive recovered from the supplied BMW corpus:

```text
BMW_M3_E36.bff
SHA-256 c31d34a0a7cab04bcff693fa0cbda3400f50d690a9c8bb2521b2882fc2a68d70
```

The existing `SHIFT.BMWVHFHierarchyRootFrame/1` builder revalidates the admitted
logical resource, archive entry, decoded payload hash, exact root node,
MatrixNumber, parent chain, and matrix convention before any numeric relation is
evaluated.

## OUTPUT

Exact generated root packet:

```text
evidence/bmw_vhf_hierarchy_root_frame.json
format = SHIFT.BMWVHFHierarchyRootFrame/1
```

Retail VHF facts:

```text
path            vehicles/bmw_m3_e36/bmw_m3_e36.vhf
entry_index     1083
decoded_size    88599
decoded_sha256  e08887d17d9e34e703a385260f41017fc19acbebc3405614b375e81766b4bd51
Root MatrixNumber = 0
parent chain      = [0]
Offset            = (0,0,0)
Orientation       = (0,0,0,1)
```

Under the existing VHF convention, the exact root world matrix and its D3D
row-vector transpose are both identity.

The selected first-bootstrap delta is independently positive:

```text
delta_local = (0,0,0)
producer    = FUN_00795d60
```

The already-proven formula is:

```text
M_vhf_root_to_outer = M_vhf_root_to_model * T(delta_local)
M_outer_to_vhf_root = inverse(M_vhf_root_to_model * T(delta_local))
```

Therefore for this selected first bootstrap:

```text
M_vhf_root_to_model = I
T(delta_local)       = I
M_vhf_root_to_outer  = I
M_outer_to_vhf_root  = I
```

Positive numeric contract:

```text
evidence/bmw_outer_vhf_numeric_relation.json
format = SHIFT.BMWOuterVHFNumericRelation/1
```

## GATES_CHANGED

New positive gate:

```text
outer_vehicle_root_to_VHF_relation_numeric_matrix_ready = true
```

Still fail-closed:

```text
BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready = false
BODY0_bind_frame_proof_ready                         = false
vehicle_world_transform_ready                        = false
```

The selected numeric matrix happens to be identity. This does **not** widen the
semantic proof from `fixed_affine` to global identity. Identity is a numeric
result of the exact selected first-bootstrap inputs; the semantic relation
remains setup-fixed affine.

## CONSUMER

Immediate S3 composition:

```text
selected BMW BODY0 -> outer Vehicle numeric matrix
+
SHIFT.BMWOuterVHFNumericRelation/1
-> BODY0 -> canonical BMW VHF root numeric matrix
-> SHIFT.BMWBody0BindFrameProof/1
```

## LIMITS

- first explicit native primary-player vehicle bootstrap only;
- no restart/mode-switch relation is claimed;
- no identity semantics are inferred from `MatrixNumber=0` or from an
  identity-valued matrix;
- no synthetic test matrix satisfies the retail proof;
- no BODY0 bind-frame or vehicle-world-transform gate is preclaimed;
- no runtime capture or original-game execution is used.

## TESTS

`tests/test_ghidra_bmw_outer_vhf_numeric_relation.py` covers matrix composition,
inversion, hash/MatrixNumber drift, singular matrices, nonzero-delta scope drift,
and exact committed retail packet identities.

`tests/test_single_process_coordination.py` requires S1/S2 positive, S3 current,
and all post-S2 semantic gates fail-closed.

## NEXT_STEP

Compose the already-positive selected BMW BODY0 -> outer matrix with this exact
outer -> VHF matrix and publish positive `SHIFT.BMWBody0BindFrameProof/1`.
