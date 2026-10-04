# Process 1 — BMW BODY0 to outer Vehicle-root bind relation

## Blocker removed

This proof narrows the remaining `SHIFT.BMWBody0BindFrameProof/1` gap. The
construction-side SDF `pos/ori -> persistent BODY origin/basis` continuity is
already proven. What was still opaque was the affine relation between the
persistent chassis BODY and the outer retail `Vehicle` transform used by the
vehicle assembly.

The new contract is:

```text
SHIFT.BMWBody0VehicleRootBindRelation/1
```

It proves the relation **symbolically** and deliberately does not invent the
BMW-specific numeric offset or equate the outer `Vehicle` root with the VHF
hierarchy root.

## Exact retail anchors

The builder validates the retail executable identity (`SHIFT.exe`, MD5
`705af8b420e5eb1e3834ac43d5533c6b`) and exact address/size/calling-convention/
mnemonic fingerprints for these functions:

- `FUN_007927c0` — outer `Vehicle` transform setter;
- `FUN_007633b0` — HDVehicle chassis transform setter;
- `FUN_00747b90` — exact three-double vector subtraction;
- `FUN_007b5ac0` — connected pmodel/BODY pose setter;
- `FUN_0075bbd0` — reverse BODY0-local to vehicle-root projection path;
- `FUN_0076df50` — HDVehicle initialization bridge;
- `FUN_007615c0` — SDF chassis BODY selection;
- `FUN_0076b280` — producer of the three-double `offset33b` state.

The direct callsites required by the proof are also validated from
`callgraph.jsonl`, including `FUN_007927c0 -> FUN_007633b0`,
`FUN_007633b0 -> FUN_00747b90`, `FUN_007633b0 -> FUN_007b5ac0`, and the
initialization edges from `FUN_0076df50`.

## Source-backed semantic join

Audited `SHIFT.exe.c` establishes:

```text
O_BODY0_world = P_vehicle_world - R_vehicle * offset33b
```

where

```text
offset33b = {
    HDVehicle+0x33b0,
    HDVehicle+0x33b8,
    HDVehicle+0x33c0
}
```

The reverse vehicle/wheel export path independently gives:

```text
q_vehicle_root = q_BODY0_local - offset33b
```

The two directions agree. Therefore, at bind/assembly time, the proven
BODY0-local -> outer-`Vehicle`-root relation has identity rotation and symbolic
translation `-offset33b`.

In the established D3D row-vector affine convention:

```text
M_BODY0_to_outer_vehicle_root =
[ 1  0  0  0 ]
[ 0  1  0  0 ]
[ 0  0  1  0 ]
[-ox -oy -oz 1 ]
```

with `(ox, oy, oz) = offset33b`.

The global aliases also line up exactly:

```text
0x00c13700 + 0x33a0 = 0x00c16aa0  # chassis BODY pointer
0x00c13700 + 0x33b0 = 0x00c16ab0  # offset33b.x
```

so the outer Vehicle path and HDVehicle path are referring to the same global
vehicle state rather than independent copies.

## Proof boundary

The semantic equations above are marked `source-backed-decompiler`, anchored to
exact retail function fingerprints and callsites. They are not mislabeled as a
full instruction-level semantic proof.

The following remain fail-closed:

```text
BMW_numeric_offset33b_ready                         = false
outer_vehicle_root_to_VHF_vehicle_root_ready       = false
BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready = false
BODY0_bind_frame_proof_ready                       = false
vehicle_world_transform_ready                      = false
```

No identity translation is assumed. No VHF-root equality is assumed. No new
runtime capture or original-game execution is used by this proof.

## Remaining minimal blockers

1. Recover the exact BMW values at `HDVehicle+0x33b0/+0x33b8/+0x33c0` after
   `FUN_0076b280`, either from an existing exact resource/init path or from a
   narrowly targeted value witness.
2. Prove the retail static/source-backed join from the outer `Vehicle` root to
   the VHF hierarchy vehicle-root frame, or recover the exact affine delta if
   they are not identical.

Once both are closed, the symbolic matrix in this contract can be materialized
into the numeric `BODY0-local -> VHF vehicle-root` bind matrix required by
`SHIFT.BMWBody0BindFrameProof/1`.
