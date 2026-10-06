# Process 1 — outer Vehicle affine -> exact BMW VHF runtime owner

## BLOCKER

**Какой конкретный blocker первого playable Linux vertical slice снимает эта работа?**

`SHIFT.BMWBody0BindFrameProof/1` still needs the exact outer Vehicle-root ->
canonical BMW VHF `HIERARCHY` root relation.

The prior proof state had two independently positive facts:

1. `SHIFT.OuterVehicleRenderSnapshotAffineBridge/1` proves the physical outer
   Vehicle snapshot -> SMS participant render-affine path.
2. `SHIFT.BMWVehicleRenderModelResourceJoin/1`, through the already-positive
   `SHIFT.VehicleRenderHierarchyResourceOwnerJoin/1`, proves that the selected
   BMW Vehicle Render Model materialized by the participant is exactly
   `vehicles/bmw_m3_e36/bmw_m3_e36.vhf`.

What was still implicit was the executable-side join between the affine carrier
and that exact BMW runtime render-model owner.

## INPUT

```text
SHIFT.OuterVehicleRenderSnapshotAffineBridge/1
SHIFT.VehicleRenderHierarchyResourceOwnerJoin/1
SHIFT.BMWVehicleRenderModelResourceJoin/1
```

No new runtime capture and no new renderer-wide reverse engineering are used.
The builder consumes only the committed positive evidence contracts and rejects
any input that already preclaims the downstream frame-identity gate.

## OUTPUT

`tools/ghidra/build_outer_vehicle_bmw_vhf_runtime_owner_affine_join.py` emits:

```text
SHIFT.OuterVehicleBMWVHFRuntimeOwnerAffineJoin/1
```

The committed positive artifact is:

```text
evidence/process1_outer_vehicle_bmw_vhf_runtime_owner_affine_join.json
```

It proves the following executable-side chain:

```text
outer Vehicle
  -> exact vehicle-slot double-buffer snapshot
  -> SMS participant root snapshot
  -> participant root affine
       rotation    = participant+0x1028
       translation = participant+0xa10/+0xa14/+0xa18
  -> FUN_004a8c20(...)
       render-model owner = participant+0x1340
  -> selected Vehicle Render Model owner
  -> BMW_M3_E36.vhf
  -> vehicles/bmw_m3_e36/bmw_m3_e36.vhf
```

The translation relation remains the already-proven retail equation:

```text
P_runtime_owner = P_outer + R_outer * delta_local

delta_local = outerVehicle[+0x19c,+0x1a0,+0x1a4]
```

Rotation is recorded only as common-source provenance through the retail
normalize -> matrix-to-quaternion -> participant-root-quaternion -> derived
matrix path. Bitwise round-trip identity is not claimed.

## CONSUMER

The immediate consumer is the final Process 1 frame adjudication after Process 3
publishes exact resource-local semantics for the canonical BMW VHF
`HIERARCHY Root`:

```text
SHIFT.OuterVehicleBMWVHFRuntimeOwnerAffineJoin/1
             +
Process 3 exact BMW VHF HIERARCHY Root local/frame semantics
             |
             v
outer Vehicle-root == VHF vehicle-root
OR exact fixed affine delta
             |
             v
BODY0-local -> VHF vehicle-root numeric relation
             |
             v
SHIFT.BMWBody0BindFrameProof/1
```

This means Process 3 no longer needs to prove executable ownership or rediscover
which runtime render model receives the outer-derived affine. It only needs the
resource-local root/frame facts assigned to it by the V4 blocker swarm.

## Gates

New positive gates:

```text
outer_vehicle_affine_to_canonical_BMW_VHF_runtime_owner_ready = true
canonical_BMW_VHF_runtime_affine_carrier_ready                = true
```

Still deliberately false:

```text
outer_vehicle_root_to_VHF_vehicle_root_ready         = false
outer_vehicle_root_to_VHF_fixed_affine_delta_ready   = false
BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready = false
BODY0_bind_frame_proof_ready                         = false
vehicle_world_transform_ready                        = false
```

## Explicit limits

The proof does **not** claim any of the following:

- `participant+0x1340` runtime render-model owner is itself the VHF
  `HIERARCHY Root` node;
- resource identity implies coordinate-frame identity;
- an identity-valued VHF root matrix, if observed, automatically proves dynamic
  outer/VHF identity;
- `FUN_004ae150` is a root setter;
- callgraph adjacency proves ownership;
- equal numeric values or visual agreement prove provenance.

Run/regenerate:

```bash
python3 tools/ghidra/build_outer_vehicle_bmw_vhf_runtime_owner_affine_join.py \
  --json-out /tmp/process1_outer_vehicle_bmw_vhf_runtime_owner_affine_join.json
```

The focused artifact test requires exact regeneration from the committed
upstream evidence, so any upstream proof drift fails closed.
