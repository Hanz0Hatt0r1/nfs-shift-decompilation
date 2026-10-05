# Process 1 — vehicle render root-pose transport frontier

## Playable-slice blocker

The remaining transform blocker is still the semantic join from the proven
outer Vehicle root to the canonical BMW VHF vehicle-root/assembly frame.  This
phase freezes an independent SMS/GraphicsEngine-side transport path so the next
proof can join two source-backed domains instead of continuing from one
car-body branch only.

It deliberately does **not** claim that an SMS snapshot is already the outer
Vehicle frame or that a RenderHierarchy node-local matrix is a vehicle world
root.

## Frozen retail path

`SHIFT.VehicleRenderRootPoseTransportFrontier/1` validates the retail executable
identity, exact mnemonic fingerprints and these direct edges:

```text
FUN_0070db00 -> FUN_00481e20 -> FUN_0047fa40

FUN_004848bc
  -> FUN_00481e20
  -> FUN_00483540 -> FUN_00438da0
  -> FUN_0042fc90
  -> FUN_004ae150

FUN_0047c9f0 -> FUN_00480700
FUN_00480700 -> FUN_0042fc90
FUN_00480700 -> FUN_004a8c20
```

This establishes a bounded snapshot/copy/derived-state/render-consumer
neighborhood independently from the outer Vehicle/car-body frontier.

## Non-gating decompiler observations

The current decompiler output strongly suggests the following byte layout:

```text
participant + 0x110   source vehicle snapshot
participant + 0xA00   render snapshot
participant + 0xA00   root quaternion
participant + 0xA10   root position x
participant + 0xA14   root position y
participant + 0xA18   root position z
participant + 0x1028  derived rotation matrix
participant + 0x1340  vehicle render-model

vehicle slot + 0xD70  first snapshot buffer
snapshot stride       0x8F0
vehicle slot + 0x1F50 active-buffer selector
```

These offsets are useful for selecting the next instruction export, but they are
**not** proof inputs and open no readiness gate.  The contract records them with
`admissibility = instruction-proof-pending`.

The source-level behavior motivating the frontier is:

- `FUN_0070db00` copies the selected vehicle-slot snapshot through
  `FUN_00481e20`;
- `FUN_00481e20` begins with the direct-copy helper `FUN_0047fa40`;
- `FUN_00483540` reaches `FUN_00438da0`, which is the matrix-construction helper
  candidate for the root quaternion;
- `FUN_004848bc` consumes the copied participant snapshot and reaches both the
  vehicle hierarchy node-update lane and matrix helpers;
- `FUN_00480700` reaches a vehicle-render-model world-point consumer through
  `FUN_004a8c20`.

The last item is intentionally classified as a secondary world-space consumer,
not as a VHF root setter.

## Run the frontier

```bash
python tools/ghidra/build_vehicle_render_root_pose_transport_frontier.py \
  out/shift_ghidra_database \
  --json-out out/vehicle_render_root_pose_transport_frontier.json
```

## Next instruction proof

Export exactly the functions listed by the generated
`targeted_instruction_worklist`, then prove:

1. the active `0x8F0` vehicle-slot snapshot selection in `FUN_0070db00`;
2. the source/destination receiver-relative root-pose fields through
   `FUN_00481e20`/`FUN_0047fa40`;
3. the quaternion source and derived rotation-matrix destination used by
   `FUN_00483540`/`FUN_00438da0`;
4. the position fields and complete world-affine construction in
   `FUN_004848bc`/`FUN_00480700`;
5. the external GraphicsEngine/RenderHierarchy owner of that affine, keeping
   `FUN_004ae150` node-local palette updates separate from the root transform.

Only after that owner is joined to the source-backed VHF runtime object may the
outer Vehicle -> VHF identity/fixed-delta gates be reconsidered.

## Important negative result from the parallel car-body frontier

Decompiler inspection of the newly added `FUN_007a3d60` frontier shows direct
collision semantics: it formats `COLLISION_CONVEX_%s_%x`, resolves the
`rubber tyre` material, constructs four wheel collision entries through
`FUN_00778fb0`, and only then copies an object/name value through
`thunk_FUN_00d5bf10`.  Therefore `_WHEEL_*_LODA` names alone must not promote
that branch to RenderHierarchy/VHF identity.  A later instruction-level
negative-classification pass should formalize this observation before retiring
that branch as a VHF candidate.
