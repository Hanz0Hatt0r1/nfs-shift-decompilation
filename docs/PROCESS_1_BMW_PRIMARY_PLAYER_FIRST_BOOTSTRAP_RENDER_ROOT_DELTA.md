# Process 1 — BMW primary-player first-bootstrap render-root delta

## BLOCKER

**Какой конкретный blocker первого playable Linux vertical slice снимает эта работа?**

Merged `SHIFT.OuterVehicleBMWVHFRootRelation/1` proves the exact outer
Vehicle-root -> canonical BMW VHF HIERARCHY-root relation is setup-fixed affine,
but its matrix is still non-numeric because the selected BMW values at
`outerVehicle+0x19c/+0x1a0/+0x1a4` were not materialized.

This stage closes those three values for the **first explicit native
primary-player vehicle bootstrap** used by the Silverstone + BMW vertical slice.
It does not claim the same values after a restart, mode transition, or world
origin update.

## INPUT

Positive upstream contracts:

```text
SHIFT.OuterVehicleBMWVHFRootRelation/1
SHIFT.BMWOffset33bNativeSessionSelection/1
```

Exact retail static evidence:

```text
SHIFT.exe MD5
705af8b420e5eb1e3834ac43d5533c6b

SHIFT.exe.c SHA-256
512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9
```

The builder also revalidates exact function ABI/fingerprints from
`functions.jsonl` and exact incoming direct calls from `callgraph.jsonl`.

The selected native role is an explicit vertical-slice policy:

```text
role = primary-player
PhysicsParticipant spawn config +0x10 = 0
first vehicle bootstrap = true
```

It is validated against retail semantics but is **not** presented as an observed
retail live-session default.

## PROOF

### 1. Role 0 is the retail primary-participant branch

`PhysicsParticipant::Restart` (`FUN_0074ddc3`) performs:

```text
spawn_config+0x10
  -> FUN_00797fd0(Vehicle, role, 0, 1)
  -> Vehicle+0x234 = role

if spawn_config+0x10 == 0:
    DAT_00c10b34 = participant

then:
    Vehicle::InitVehicle
```

Thus the explicit native primary-player policy selects the `Vehicle+0x234 == 0`
branch consumed by `FUN_00795d60`.

The retail config initializer `FUN_0074e760` also initializes `config+0x10` to
zero. This is supporting static evidence only; the contract does not promote it
to a claim about every retail live session.

### 2. The old delta is exactly zero before first InitVehicle

The Vehicle constructor subobject initializer `FUN_0079bfd0` writes:

```text
param_1[0x67] = 0   -> Vehicle+0x19c
param_1[0x68] = 0   -> Vehicle+0x1a0
param_1[0x69] = 0   -> Vehicle+0x1a4
```

The exact `Restart -> InitVehicle -> FUN_00795d60` prefix is checked for direct
touches to those fields. The reviewed prefix does not overwrite them before the
delta producer runs.

### 3. The initial origin vector is exact PE zero-fill

The three origin globals are in the virtual tail of retail `.data`, beyond its
raw file payload:

```text
.data VA             = 0x00b81000
.data virtual size   = 0x00167040
.data raw size       = 0x0003b600

DAT_00c16ab0 offset  = 0x00095ab0
DAT_00c16ab8 offset  = 0x00095ab8
DAT_00c16ac0 offset  = 0x00095ac0
```

Therefore the PE loader initializes all three to exact zero.

The related switch flag `DAT_00c19db9` is also PE zero-fill. Raw-image absolute
reference scanning finds only the reviewed `.text` references recorded in the
machine-readable handoff.

### 4. No origin update occurs on the selected first-bootstrap prefix

The direct writer of `&DAT_00c16ab0` is:

```text
FUN_0078ef00
  -> FUN_007afd20(..., &DAT_00c16ab0, ...)
```

Its exact direct callers are:

```text
FUN_0074bfd0
FUN_00794a30
FUN_0079b2d0
```

Those are switch/runtime paths. `FUN_0078ef00` is not called on the selected
first `PhysicsParticipant::Restart -> FUN_00797fd0(role=0) ->
Vehicle::InitVehicle -> FUN_00795d60` prefix, and the retail image contains no
absolute function-pointer reference to `FUN_0078ef00`.

This proof is deliberately scoped to that first bootstrap. It does not claim
that the origin vector stays zero later.

### 5. Numeric delta

For `Vehicle+0x234 == 0`, `FUN_00795d60` overrides the geometry-derived
candidate with:

```text
new +0x19c = old +0x19c - DAT_00c16ab0
new +0x1a0 = old +0x1a0 - DAT_00c16ab8
new +0x1a4 = old +0x1a4 - DAT_00c16ac0
```

With constructor state `(0,0,0)` and first-bootstrap origin `(0,0,0)`:

```text
delta_local = (0, 0, 0)
```

## OUTPUT

`tools/ghidra/build_bmw_primary_player_first_bootstrap_render_root_delta.py`
emits:

```text
SHIFT.BMWPrimaryPlayerFirstBootstrapRenderRootDelta/1
```

Committed handoff:

```text
evidence/process1_bmw_primary_player_first_bootstrap_render_root_delta.json
```

New positive gate:

```text
BMW_primary_player_first_bootstrap_render_root_delta_numeric_ready = true
```

Consumed upstream semantic gates stay positive:

```text
outer_vehicle_root_to_VHF_vehicle_root_ready       = true
outer_vehicle_root_to_VHF_fixed_affine_delta_ready = true
```

These remain fail-closed:

```text
outer_vehicle_root_to_VHF_relation_numeric_matrix_ready = false
BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready    = false
BODY0_bind_frame_proof_ready                            = false
vehicle_world_transform_ready                           = false
```

## CONSUMER

Immediate Process 1 continuation:

```text
exact BMW VHF HIERARCHY Root row-vector matrix
+
delta_local = (0,0,0)
+
SHIFT.OuterVehicleBMWVHFRootRelation/1
-> exact numeric outer Vehicle -> VHF-root matrix
-> compose existing selected BMW BODY0 -> outer matrix
-> SHIFT.BMWBody0BindFrameProof/1
```

Process 2 may consume this numeric delta stage, but final relation/BODY0
admission remains fail-closed until Process 1 publishes the numeric relation and
final bind proof.

## LIMITS

This contract does **not** claim:

- zero delta for non-primary vehicles;
- zero delta after restart or role/mode switching;
- zero origin after any `FUN_0078ef00` update;
- that the explicit native primary-player policy is a captured retail session;
- a numeric VHF-root matrix;
- a final BODY0 bind frame;
- a vehicle world transform.

No original-game execution or runtime capture is used.

## REPRODUCE

```bash
python3 tools/ghidra/build_bmw_primary_player_first_bootstrap_render_root_delta.py \
  evidence/process1_outer_vehicle_bmw_vhf_root_relation.json \
  evidence/bmw_offset33b_native_silverstone_session.json \
  /path/to/functions.jsonl \
  /path/to/callgraph.jsonl \
  /path/to/SHIFT.exe.c \
  /path/to/SHIFT.exe \
  --native-role primary-player \
  --first-vehicle-bootstrap \
  --json-out out/bmw_primary_player_first_bootstrap_render_root_delta.json
```
