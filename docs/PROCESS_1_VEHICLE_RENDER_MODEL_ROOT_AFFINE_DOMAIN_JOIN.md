# Process 1 — vehicle Render Model root-affine domain join

## BLOCKER

**Какой конкретный blocker первого playable Linux vertical slice снимает эта работа?**

`SHIFT.BMWBody0BindFrameProof/1` is blocked by the exact outer Vehicle-root ->
canonical BMW VHF HIERARCHY-root relation. The existing proofs separately establish
(1) outer Vehicle -> render-snapshot root affine and (2) the exact BMW VHF
resource/root frame. The missing semantic join is whether that participant root
affine belongs to the same materialized Vehicle Render Model coordinate domain.

## INPUT

- `SHIFT.BMWVehicleRenderModelResourceJoin/1`;
- `SHIFT.OuterVehicleRenderSnapshotAffineBridge/1`;
- retail `SHIFT.exe.c` SHA-256 `512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`;
- exact retail function fingerprints for `FUN_00483c50`, `FUN_00480700`, and
  `FUN_004a8c20`.

## OUTPUT

`SHIFT.VehicleRenderModelRootAffineDomainJoin/1` proves:

```text
selected descriptor +0x54 (Vehicle Render Model)
  -> FUN_004aecd0(participant+0x1340, ...)

participant root affine
  rotation    = participant+0x1028
  translation = participant+0xa10/+0xa14/+0xa18
  -> FUN_004a8c20(participant+0x1340, root_affine)

FUN_004a8c20
  model-local point source = renderModel+0x918
  validity flags           = renderModel+0x8f0
  row-vector affine slots  = 0/4/8/12, 1/5/9/13, 2/6/10/14
  model identity forward   = renderModel+0x174 -> FUN_00693940
```

Therefore the participant root affine is the local-to-world affine for coordinates
owned by the same materialized Vehicle Render Model domain that the positive BMW
resource join identifies as `vehicles/bmw_m3_e36/bmw_m3_e36.vhf`.

This is an ownership/coordinate-domain proof. It does **not** yet apply the VHF
`HIERARCHY Root` matrix.

## CONSUMER

Process 1 exact root composition:

```text
SHIFT.OuterVehicleRenderRootDeltaProvenance/1
+ SHIFT.OuterVehicleRenderSnapshotAffineBridge/1
+ SHIFT.VehicleRenderModelRootAffineDomainJoin/1
+ SHIFT.BMWVHFHierarchyRootFrame/1
-> exact outer Vehicle-root / BMW VHF HIERARCHY-root relation
```

## GATES_CHANGED

```text
vehicle_render_model_root_affine_domain_join_ready = true
```

These remain false:

```text
outer_vehicle_root_to_VHF_vehicle_root_ready
outer_vehicle_root_to_VHF_fixed_affine_delta_ready
BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready
BODY0_bind_frame_proof_ready
vehicle_world_transform_ready
```

## LIMITS

- `FUN_004ae150` remains node-local hierarchy/palette work and is not promoted to
  a root setter.
- No identity-valued VHF root matrix is treated as frame identity.
- No numeric outer->VHF matrix is invented.
- No runtime capture or original-game execution is used.

## TESTS

`tests/test_ghidra_vehicle_render_model_root_affine_domain_join.py` covers the
positive exact-domain join plus resource preclaim rejection, affine-consumer drift,
retail function fingerprint drift, and local-point transform witness drift.

## NEXT_OWNER

Process 1: compose the positive exact BMW VHF HIERARCHY root frame with this proven
Vehicle Render Model root-affine domain and the setup-produced
`+0x19c/+0x1a0/+0x1a4` relation. Publish the outer/VHF relation immediately once
that composition is positive.
