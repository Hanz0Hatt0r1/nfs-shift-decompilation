# Process 1 — BMW BODY0 construction target identity

## Playable-slice blocker removed

The native Linux slice still needs a proven BMW BODY0 bind frame before the
persistent physics body can drive the vehicle world transform and Vulkan vehicle
composition.

The construction side was previously split into two already-proven facts:

- `SHIFT.BMWBody0ConstructionPoseStores/1` finds the exact machine/p-code writes
  overlapping persistent BODY origin/basis storage, but deliberately does not
  name their target object;
- `SHIFT.BMWBody0ConstructionBindContinuity/1` proves SDF `BODY.pos` and
  `BODY.ori` semantics into persistent BODY origin/basis, but still leaves the
  final SDF-model -> VHF vehicle-root frame relation open.

This phase closes the missing target identity join:

```text
construction pose writer target
  -> persistent 0x170 BODY record
  -> exact BMW chassis BODY index 0 ("body")
```

New contract:

```text
SHIFT.BMWBody0ConstructionTargetIdentity/1
```

Tool:

```text
tools/ghidra/build_bmw_body0_construction_target_identity.py
```

## Retail construction invariant

The exact BMW loader `FUN_007b6900` performs a count pass over `[BODY]`
sections, allocates the persistent BODY array with stride `0x170`, and stores its
base at loader `+0x14`.

Before the second parse pass the BODY ordinal is reset to zero. Every `[BODY]`
section is then parsed into one descriptor and passed to:

```text
FUN_007b3670(loader, descriptor, &body_ordinal)
```

`FUN_007b3670` computes one persistent record as:

```text
*(loader + 0x14) + body_ordinal * 0x170
```

and uses that same record for all of the following:

```text
BODY.pos -> persistent origin +0x00/+0x08/+0x10
BODY.ori -> FUN_007bbb10(same record, ...)
         -> persistent basis +0xd4..+0xf4
```

Only after those writes does the builder increment the BODY ordinal exactly
once.

The Phase-404 BMW resource contract independently fixes the exact BODY order as:

```text
0  body
1  fl_spindle
2  fr_spindle
3  fl_wheel
4  fr_wheel
5  rl_spindle
6  rr_spindle
7  rl_wheel
8  rr_wheel
9  fuel_tank
10 driver_head
```

Therefore the first construction target is exactly:

```text
*(loader + 0x14) + 0 * 0x170
```

and is the BMW chassis BODY0 named `body`.

## Fail-closed gates

The builder requires all of these before asserting target identity:

- exact retail `SHIFT.exe` MD5;
- exact mnemonic fingerprints for `FUN_007b6900`, `FUN_007b3670`, and
  `FUN_007bbb10`;
- exact direct edges `0x007b6e8f -> FUN_007b3670` and
  `0x007b37c8 -> FUN_007bbb10`;
- exact Phase-404 BMW archive/SDF identity and full BODY order;
- completed `SHIFT.BMWBody0ConstructionPoseStores/1` with no structural
  ambiguity;
- at least one origin STORE candidate specifically inside `FUN_007b3670`;
- positive construction origin and basis continuity;
- no upstream preclaim of the final BODY0 bind frame.

A STORE candidate in another helper, a basis-only candidate, BODY-order drift,
function/callsite drift, or incomplete pose-store discovery blocks the proof.

## Handoff

A positive result asserts:

```text
persistent_BODY_target_identity_proven = true
BODY0_pointer_at_construction_pose_write_ready = true
origin_writer_target_is_BODY0 = true
basis_writer_target_is_BODY0 = true
```

If the exact BODY0 resource values have already been materialized through the
continuity contract, their existing `BODY0_local_to_SDF_model_bind_pose_ready`
state is preserved. This phase does not invent those values.

These remain false:

```text
SDF_model_to_VHF_vehicle_root_frame_relation_ready = false
BODY0_bind_frame_proof_ready = false
vehicle_world_transform_ready = false
```

The next shortest blocker is now only the static coordinate-frame relation:

```text
SDF model construction frame -> VHF vehicle-root / assembly frame
```

Pointer ancestry, common owner names, or the shared `+0x340` child expression
must not be treated as proof of frame identity.

## Reproduction

Given existing reports:

```bash
python3 tools/ghidra/build_bmw_body0_construction_target_identity.py \
  out/shift_ghidra_database \
  evidence/bmw_m3_e36_physics_intake_phase404.json \
  out/bmw_body0_construction_pose_stores.json \
  evidence/bmw_body0_construction_bind_continuity.json \
  --json-out out/bmw_body0_construction_target_identity.json
```

No original-game execution or new runtime capture is required.
