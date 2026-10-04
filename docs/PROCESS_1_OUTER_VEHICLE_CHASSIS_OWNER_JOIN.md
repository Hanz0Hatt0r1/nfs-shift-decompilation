# Process 1 — outer Vehicle car-body/CHASSIS owner join

## Playable-slice blocker reduced

The playable Linux slice still requires a positive `SHIFT.BMWBody0BindFrameProof/1` before the retail BODY0 pose can drive the persistent BMW world transform and live Vulkan vehicle upload.

The previous outer-Vehicle receiver pass left two static continuations:

```text
FUN_007afb60 -> FUN_007aef50

proven HDVehicle control
  -> [HDVehicle+0x3fe8]
  -> dereference
  -> +0x340
  -> FUN_007ac2f0
```

The targeted retail export supplied for this phase contains:

```text
FUN_0076df50  MWL::Core::HighDetailVehicle::Init
FUN_007ac4d0  car-body / CHASSIS initialization domain
FUN_007aef50  forwarded helper
```

Together with the previous exact four-function export, it closes the anonymous outer-owner search without inventing a VHF/frame identity.

New machine-readable contract:

```text
SHIFT.OuterVehicleChassisOwnerJoin/1
```

Analyzer:

```text
tools/ghidra/analyze_outer_vehicle_chassis_owner_join.py
```

## Exact retail owner join

`FUN_0076df50` preserves entry `ECX` in `ESI`:

```text
0x0076df6e  MOV ESI,ECX
```

The solver setup call uses that exact HDVehicle receiver:

```text
0x0076e236  MOV ECX,ESI
0x0076e238  CALL FUN_007615c0
```

The car-body/CHASSIS initialization call then takes this machine path:

```text
0x0076e243  MOV EAX,[ESI+0x3fe8]
0x0076e249  MOV EDX,[ESI+0x66b4]
0x0076e24f  LEA ECX,[EAX+0x10c]
0x0076e255  PUSH ECX
0x0076e256  MOV ECX,[EAX]
0x0076e258  PUSH 0x1
0x0076e25a  PUSH EDX
0x0076e25b  ADD ECX,0x340
0x0076e261  CALL FUN_007ac4d0
```

Therefore the physical `FUN_007ac4d0` receiver expression is:

```text
*([HDVehicle+0x3fe8]) + 0x340
```

The previous proven HDVehicle-control lane reaches `FUN_007ac2f0` through the same relative expression:

```text
EDX = [HDVehicle+0x3fe8]
ECX = [EDX]
ECX += 0x340
CALL FUN_007ac2f0
```

This proves a common **HDVehicle-relative car-body/CHASSIS child domain** between initialization and the later post-transform update path.

It does not prove that two calls at different times contain the same runtime pointer value, and it does not prove that this child frame equals the VHF vehicle-root frame.

## `FUN_007aef50` branch eliminated

`FUN_007aef50` contains no calls and no receiver writes. Its complete receiver data surface is nine floats:

```text
this + 0x00 / 0x04 / 0x08
this + 0x0c / 0x10 / 0x14
this + 0x18 / 0x1c / 0x20
```

It multiplies those values by a three-component input vector and writes exactly three float results through the output pointer at `+0x00/+0x04/+0x08`.

Thus:

```text
FUN_007afb60 -> FUN_007aef50
```

is a computational matrix/vector lane, not an owner-forward path. It is removed from further VHF-owner traversal.

## `FUN_007ac4d0` semantic anchors

The Ghidra evidence database pins the function to these exact strings/xrefs:

```text
0x00ab5b74  "car body"  -> 0x007ac504
0x00abc55c  "CHASSIS"   -> 0x007acba8
0x00b0c6d8  ".joi.xml"  -> 0x007acc55
```

The function saves its receiver in `EDI` and exposes concrete subobject/owner edges including:

```text
EDI + 0x30  -> FUN_007519d0
[EDI+0x34]  -> FUN_00777cd0
EDI + 0x534 -> FUN_0049f980 / FUN_007a5a40 / FUN_007a3d60
```

These anchors identify the domain as car-body/CHASSIS assembly logic. They are not promoted to VHF hierarchy identity.

## Negative bind-writer result

The later `FUN_007ac2f0` post-transform path reads transform-source values from its receiver at:

```text
+0x90 / +0x94 / +0x98
+0x160 / +0x164 / +0x168
+0x178
```

The exact direct receiver stores inside `FUN_007ac4d0` are instead at:

```text
+0x4c / +0x50 / +0x54 / +0x58 / +0x5c / +0x60
+0x148 / +0x14c / +0x150
+0x1a8 / +0x1ac / +0x1b0 / +0x1b4 / +0x1b8 / +0x1bc / +0x1c0
+0x80c
```

The intersection is empty.

Therefore `FUN_007ac4d0` is **not proven to be the direct initialization writer** for the transform-source fields consumed by `FUN_007ac2f0`.

This is deliberately narrower than saying no indirect callee ever writes those fields. The analyzer does not make that claim.

## Consequence for the blocker graph

The outer Vehicle fan-out is no longer worth expanding as a parallel owner search:

```text
FUN_007876e0                         eliminated: scalar/vector leaf
FUN_007afb60 -> FUN_007aef50         eliminated: matrix/vector leaf
FUN_007633b0 -> FUN_007ac2f0         retained: proven HDVehicle car-body child
FUN_007ac4d0                          same HDVehicle-relative child at init
```

But the surviving child-domain join does not provide the required numeric/static frame relation:

```text
BODY0 local frame
  -> VHF vehicle-root frame
```

so these remain false:

```text
outer_vehicle_root_to_VHF_vehicle_root_ready = false
BODY0_bind_frame_proof_ready                 = false
vehicle_world_transform_ready                = false
```

## Next priority

The shortest remaining transform-semantic path is no longer another outer-Vehicle receiver export. Return to the source-backed BODY construction side-effect/write chain represented by `SHIFT.BMWBody0ConstructionPoseStores/1` and follow the next concrete writer/side-effect until both of these joins are static:

```text
writer target -> persistent BMW chassis BODY0
writer values -> BODY0 bind origin/basis
```

Only after those are positive should the resulting BODY0-local bind frame be composed with the already-proven Phase 645 VHF vehicle-root/body-MEB transform.

Do not revive `FUN_007aef50`, infer identity from the common `+0x340` expression, or treat the `car body`/`CHASSIS` names as a frame matrix.

## Reproduction

```bash
python3 tools/ghidra/analyze_outer_vehicle_chassis_owner_join.py \
  out/shift_ghidra_database \
  out/outer_vehicle_owner_candidates_instructions.jsonl \
  out/outer_vehicle_chassis_owner_join_instructions.jsonl \
  --json-out out/outer_vehicle_chassis_owner_join.json
```

The analyzer validates the retail executable MD5, exact function mnemonic fingerprints, exact instruction target sets/counts, semantic string witnesses, the init/update receiver paths, the matrix-helper leaf shape, and the non-intersection of direct chassis-init writes with the post-transform pose-source fields.
