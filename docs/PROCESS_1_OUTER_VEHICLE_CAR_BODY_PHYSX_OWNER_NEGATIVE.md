# Process 1 — retire car-body `+0x34` from positive VHF/root ownership

## Blocker reduced

The shortest playable Linux slice blocker remains
`SHIFT.BMWBody0BindFrameProof/1`.  Construction/BODY0 identity and the symbolic
BODY0 -> outer Vehicle relation are already proven; the remaining independent
frame edge is:

```text
outer Vehicle root -> canonical BMW VHF vehicle-root / assembly frame
```

`SHIFT.OuterVehicleChassisOwnerJoin/1` previously exposed a promising runtime
pointer at `car-body +0x34`.  `FUN_007ac2f0` consumes that pointer through
transform-looking virtual calls, so the field could easily be mistaken for a
RenderHierarchy/VHF owner.

The full retail Ghidra C export proves a different ownership domain.  This phase
adds the negative contract:

```text
SHIFT.OuterVehicleCarBodyPhysXOwnerNegative/1
```

implemented by:

```text
tools/ghidra/classify_outer_vehicle_car_body_physx_owner.py
```

## Source-backed ownership chain

The classifier validates the exact retail `SHIFT.exe` identity through the
existing Ghidra database and requires the ready
`SHIFT.OuterVehicleChassisOwnerJoin/1` loaded-pointer edge:

```text
car-body +0x34 -> FUN_00777cd0
```

It then audits only six bounded function bodies from `SHIFT.exe.c`.

### 1. PhysX owner creation

`FUN_007506b0` creates the SDK explicitly:

```text
DAT_00c13384 = NxCreatePhysicsSDK(...)
```

The same function contains the source/debug witnesses
`PhysicsSystem.cpp` and `Failed to Create PhysX SDK`, then obtains
`DAT_00c133ac` from the SDK object through virtual slot `+0x10`.

### 2. `car-body +0x34` producer

`FUN_007798a0` obtains `piVar11` through `DAT_00c133ac` virtual slot `+0x1c`
and writes:

```text
*param_2   = param_3
param_2[1] = piVar11
piVar11[1] = param_2
```

`FUN_007ac4d0` calls that builder with:

```text
param_2 = car-body +0x30
```

and immediately reloads:

```text
param_4 = *(car-body +0x34)
FUN_00777cd0(param_4)
```

Therefore the second word of the builder output pair is physically:

```text
car-body +0x34 = piVar11
```

### 3. Symmetric destruction

`FUN_007ab8e0` reloads `car-body +0x34`, releases it through the same
`DAT_00c133ac` owner at virtual slot `+0x20`, then clears the field.

The create and release boundaries therefore share the same object rooted in the
PhysX SDK creation path.

## Negative conclusion

A ready report proves:

```text
car_body_plus_0x34_physx_owned_lifetime_proven = true
car_body_plus_0x34_is_admissible_standalone_VHF_identity_anchor = false
car_body_plus_0x34_branch_removed_from_positive_VHF_owner_search = true
```

The exact PhysX subclass is deliberately not invented.  The contract also does
not claim that the physics object can never be referenced by rendering code.
It proves only that transform-looking virtual calls on this pointer are not
sufficient to promote the pointer to RenderHierarchy/VHF identity after its
PhysX ownership has been established independently.

## Handoff

The live P1.1 search must now exclude both known false positive branches:

```text
car-body +0x534 -> collision/material wheel lane
car-body +0x34  -> PhysX-owned object lifetime
```

The remaining admissible target is an independently identified VHF/render-resource
owner path that physically joins the outer Vehicle/car-body domain to the exact
BMW VHF vehicle-root frame.

These remain false:

```text
outer_vehicle_root_to_VHF_vehicle_root_ready = false
BODY0_bind_frame_proof_ready = false
vehicle_world_transform_ready = false
```

## Reproduction

Given the existing retail evidence database, the committed upstream owner-join
report, and a Ghidra `SHIFT.exe.c` export of the same retail binary:

```bash
python3 tools/ghidra/classify_outer_vehicle_car_body_physx_owner.py \
  out/shift_ghidra_database \
  evidence/outer_vehicle_chassis_owner_join_retail.json \
  /path/to/SHIFT.exe.c \
  --json-out out/outer_vehicle_car_body_physx_owner_negative.json
```

No original-game execution, runtime capture, broad callgraph expansion, or
renderer work is required.
