# Single process — BMW outer/VHF numeric relation frontier

## BLOCKER

**Какой конкретный blocker первого playable Linux vertical slice снимает эта работа?**

S1 is positive via `SHIFT.BMWPrimaryPlayerFirstBootstrapRenderRootDelta/1`, so
the current blocker is S2: publish a finite provenance-bearing
`M_outer_to_vhf_root` before S3 can assemble `SHIFT.BMWBody0BindFrameProof/1`.

## INPUT

Already positive on current main:

```text
SHIFT.OuterVehicleBMWVHFRootRelation/1
SHIFT.BMWPrimaryPlayerFirstBootstrapRenderRootDelta/1
SHIFT.BMWVHFHierarchyRootFrame/1              semantic/resource proof positive
```

The selected first-bootstrap delta is exact:

```text
delta_local = (0, 0, 0)
```

Therefore the already-proven row-vector formula reduces numerically to:

```text
M_outer_to_vhf_root = inverse(M_vhf_root_to_model)
```

## EXACT REMAINING DATA EDGE

The positive retail `SHIFT.BMWVHFHierarchyRootFrame/1` was generated from the
exact admitted `BMW_M3_E36.bff`, but the concrete generated JSON carrying
`vehicle_root_frame.world_matrix_row_vector` was not retained on current main.
The current conversation/Project/Library inputs also do not contain the exact
BMW archive or a derived root-frame artifact.

`MatrixNumber == 0` is not admissible evidence that the matrix is identity. The
existing identity Matrix-0 examples are test fixtures only.

Machine-readable frontier:

```text
evidence/bmw_outer_vhf_numeric_relation_frontier.json
SHIFT.BMWOuterVHFNumericRelationFrontier/1
```

## PREPARED CONSUMER

`tools/ghidra/build_bmw_outer_vhf_numeric_relation.py` accepts exactly:

1. positive `SHIFT.OuterVehicleBMWVHFRootRelation/1`;
2. positive `SHIFT.BMWPrimaryPlayerFirstBootstrapRenderRootDelta/1`;
3. the concrete positive retail `SHIFT.BMWVHFHierarchyRootFrame/1` instance.

It validates canonical BMW path/SHA/root identity, exact root-matrix provenance,
16 finite row-vector affine scalars, exact first-bootstrap delta scope, and the
fixed-affine formula. It emits:

```text
SHIFT.BMWOuterVHFNumericRelation/1
```

and promotes only:

```text
outer_vehicle_root_to_VHF_relation_numeric_matrix_ready = true
```

S3 and world-transform gates remain false.

## LIMITS

- No identity is inferred from `MatrixNumber=0`.
- No test fixture or visually plausible matrix can satisfy the retail input.
- Existing D3D9 capture lacks the canonical BMW VHF/root-frame identity needed
  to replace the resource proof.
- No new runtime capture is requested.
- No rejected owner/render-manager branches are reopened.

## TESTS

```bash
pytest -q tests/test_ghidra_bmw_outer_vhf_numeric_relation.py
```

Focused local result: `7 passed`.

The tests deliberately use a non-identity Matrix-0 fixture and verify exact
inversion, identity non-promotion, missing-matrix rejection, SHA drift rejection,
delta drift rejection, upstream numeric-preclaim rejection, and singular-matrix
rejection.

## NEXT_STEP

Retain or regenerate the exact positive retail root-frame JSON from the admitted
BMW resource, run the prepared composer, publish `SHIFT.BMWOuterVHFNumericRelation/1`
immediately, then compose S3 `SHIFT.BMWBody0BindFrameProof/1`.
