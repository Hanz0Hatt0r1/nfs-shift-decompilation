# Process 1 — retire the wheel-LOD collision branch from VHF/root search

## Blocker reduced

The current shortest playable-slice blocker remains `SHIFT.BMWBody0BindFrameProof/1`.
After the render-manager `+0xca4` direct and indirect method branches were closed
negatively, the remaining transform question is the source-backed relation from
the outer Vehicle/car-body runtime domain to the canonical BMW VHF vehicle-root.

One live candidate branch still polluted that search:

```text
HDVehicle
  -> car-body/CHASSIS child
  -> +0x534 child
  -> FUN_007a3d60
  -> wheel LOD strings
  -> thunk_FUN_00d5bf10
```

Wheel LOD names are not sufficient render/VHF evidence.  The saved retail Ghidra
database contains stronger, directly contradictory domain anchors in the same
function.

The new contract is:

```text
SHIFT.OuterVehicleCollisionLodNegative/1
```

implemented by:

```text
tools/ghidra/classify_outer_vehicle_collision_lod_branch.py
```

## Exact retail witnesses

The classifier validates retail `SHIFT.exe` MD5
`705af8b420e5eb1e3834ac43d5533c6b`, exact mnemonic fingerprints and the
already-proven `SHIFT.OuterVehicleChassisOwnerJoin/1` edge into the car-body
`+0x534` child.

Inside exact `FUN_007a3d60` it requires these string/xref witnesses:

```text
0x00b0c3c0  "rubber tyre"            -> 0x007a3f41
0x00b0c3cc  "COLLISION_CONVEX_%s_%x" -> 0x007a3f33
0x00b0c3e4  "_WHEEL_RR_LODA"         -> 0x007a3ef4
0x00b0c3f4  "_WHEEL_RL_LODA"         -> 0x007a3eea
0x00b0c404  "_WHEEL_FR_LODA"         -> 0x007a3ee0
0x00b0c414  "_WHEEL_FL_LODA"         -> 0x007a3ed6
```

It also requires the exact direct edges:

```text
FUN_007ac4d0  0x007accc3 -> FUN_007a3d60
FUN_007a3d60  0x007a3ffe -> FUN_00778fb0
FUN_007a3d60  0x007a402a -> thunk_FUN_00d5bf10
```

The combination of a collision-convex format string, rubber-tyre material name,
all four wheel LOD names and the concrete helper call is sufficient to classify
this lane as collision/material wheel-object construction evidence.  It is not
admissible as a positive RenderHierarchy/VHF identity anchor merely because the
wheel LOD names are also visual-looking names.

## Negative result

A ready report proves only:

```text
FUN_007a3d60_is_admissible_VHF_root_candidate = false
wheel_lod_name_proximity_is_render_identity    = false
branch_removed_from_outer_vehicle_to_VHF_search = true
```

It deliberately does **not** claim:

```text
outer Vehicle -> VHF relation does not exist
thunk_FUN_00d5bf10 can never participate in rendering elsewhere
all car-body +0x534 behavior is collision-only
```

The physical branch above is retired; the global frame blocker remains open.

## Next frontier

The next admissible P1.1 work is the already-independent
`SHIFT.VehicleRenderRootPoseTransportFrontier/1`, which contains positive
SMS/RenderHierarchy-side anchors such as participant render tick, hierarchy
node-local update, world-affine consumer and vehicle render-model world-point
consumer.

The required join is now narrower:

```text
independently identified SMS/RenderHierarchy runtime owner/root pose
  -> canonical BMW VHF vehicle-root/assembly frame
  -> SHIFT.BMWBody0BindFrameProof/1
```

Do not reopen the closed player-render-manager `+0xca4` branches and do not use
`FUN_007a3d60` wheel-name proximity as positive render evidence again.

## Reproduction

```bash
python tools/ghidra/classify_outer_vehicle_collision_lod_branch.py \
  out/shift_ghidra_database \
  evidence/outer_vehicle_chassis_owner_join_retail.json \
  --json-out out/outer_vehicle_collision_lod_negative.json
```

No original-game execution, new runtime capture or new Ghidra instruction export
is required.
