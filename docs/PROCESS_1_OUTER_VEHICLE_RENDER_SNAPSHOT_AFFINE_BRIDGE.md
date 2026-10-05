# Process 1 — outer Vehicle -> render snapshot affine bridge

## Playable-slice blocker reduced

`SHIFT.BMWBody0BindFrameProof/1` remains blocked on the exact relation between the proven outer Vehicle root and the canonical BMW VHF hierarchy vehicle-root. This pass closes the physical producer/consumer bridge from outer Vehicle state into the SMS render participant root affine. It does not synthesize the remaining VHF relation.

New contract:

```text
SHIFT.OuterVehicleRenderSnapshotAffineBridge/1
```

## Proven retail chain

The retail vehicle-slot manager is rooted at `DAT_00c109e0`; its slot array is exactly `+0x140 == DAT_00c10b20`, with `0x1fa0` bytes per slot. Slot creation allocates the vehicle owner, then:

```text
FUN_00715240
  -> FUN_007125e0(slot)
  -> FUN_00721ea0(owner, slot)
  -> FUN_007839a0(owner + 0x340, slot)
  -> outerVehicle + 0x848 = slot
```

The SMS participant stores its numeric vehicle index at `+0x100`, copies it to `+0xfc`, and retail machine bytes in `FUN_0047f9e0` load `[participant+0xfc]` immediately before `FUN_0070dcc0`. `FUN_0070dccf` uses that index directly as:

```text
slot = DAT_00c10b20 + index * 0x1fa0
```

`FUN_0070db00` then reads the active snapshot from:

```text
slot + 0xd70 + (slot[+0x1f50] & 1) * 0x8f0
```

The producer `FUN_00795630` writes through `outerVehicle+0x848` to the same double-buffer family and increments `slot+0x1f50` after the publish path. This proves physical slot continuity but deliberately does not claim retail scheduler cadence.

## Exact affine relation

`FUN_007927c0` stores outer position at `+0x160/+0x164/+0x168`, orientation parameters at `+0x16c/+0x170/+0x174`, and materializes the outer 3x3 orientation at `+0x178..+0x198`.

`FUN_007904f0` builds the snapshot root as:

```text
P_snapshot = P_outer + R_outer * delta_local

delta_local = outerVehicle[+0x19c,+0x1a0,+0x1a4]
```

The snapshot orientation has no independent source: the same `R_outer` is copied, normalized, converted matrix -> quaternion, and stored in the snapshot. This pass records common-source provenance; it does not claim bitwise matrix round-trip identity.

`FUN_004848bc` copies the selected source snapshot from `participant+0x110` to `participant+0xa00`. `FUN_00483540 -> FUN_00438da0` derives the render rotation matrix at `participant+0x1028` from the root quaternion. `FUN_00480700` combines that matrix with translation `participant+0xa10/+0xa14/+0xa18`, and `FUN_004a8c20` explicitly consumes affine translation slots `12/13/14` in its world-point transform.

`FUN_004ae150` remains node-local hierarchy/palette work and is not promoted to the root setter.

## Local delta producer

`FUN_00795d60`, called from the vehicle initialization/setup path `FUN_00798df0`, writes the local root delta at `+0x19c/+0x1a0/+0x1a4` from vehicle geometry/setup calculations. The field therefore has a concrete bounded producer. This proof does not yet equate that delta with the canonical BMW VHF hierarchy root offset.

## Fail-closed handoff

The contract promotes:

```text
outer_vehicle_render_snapshot_slot_identity_ready = true
outer_vehicle_to_render_root_symbolic_affine_ready = true
render_root_translation_delta_producer_bounded = true
```

It keeps false:

```text
outer_vehicle_root_to_VHF_vehicle_root_ready
outer_vehicle_root_to_VHF_fixed_affine_delta_ready
BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready
BODY0_bind_frame_proof_ready
vehicle_world_transform_ready
```

The next bounded proof is now only:

```text
FUN_00795d60-produced outerVehicle +0x19c/+0x1a0/+0x1a4
  -> canonical BMW VHF HIERARCHY vehicle-root/frame
```

Do not reopen the retired car-body `+0x34` PhysX owner, car-body `+0x534` collision LOD owner, or render-manager `+0xca4` branches.

## Reproduce

```bash
python3 tools/ghidra/analyze_outer_vehicle_render_snapshot_affine_bridge.py \
  out/shift_ghidra_database \
  /path/to/SHIFT.exe.c \
  /path/to/SHIFT.exe \
  --json-out out/outer_vehicle_render_snapshot_affine_bridge.json
```

The executable is read only for MD5 and a small set of exact machine-byte witnesses. The game is never executed; no runtime capture is required.
