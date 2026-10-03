# Process 1 — global vehicle component-base identity

## Playable-slice blocker reduced

Process 1 #1188 and Process 2 Phase 702 prove the BMW main/chassis BODY as
retail BODY index 0, but Phase 702 still describes the next identity gate as:

```text
*record+0x340 update child
  -> FUN_00794a30
  -> ? same vehicle base
  -> FUN_007615c0
```

That formulation is stricter than the already-merged static evidence requires.
The normal `FUN_00794a30` path does not forward its receiver into
`FUN_00770e80`; it forwards two 64-bit channels and calls the outer update on
`&DAT_00c13700`.

Independent Phase 633/635/636 evidence already identifies address `0x00c13700`
as the global vehicle component base used by the four-slot relation-state path.
This phase composes those two facts without relabelling the anonymous update
child as the vehicle.

No original `SHIFT.exe` execution and no new runtime capture are used.

## Contract

```text
SHIFT.GlobalVehicleComponentBaseIdentity/1
```

Builder:

```text
tools/ghidra/build_global_vehicle_component_base_identity.py
```

Frozen supporting evidence:

```text
evidence/global_vehicle_component_callsite_phase633.json
```

## Independent static lanes

### Outer-update receiver lane

`SHIFT.OuterUpdateCallsiteStatic/1` source/hash/Ghidra cross-check proves:

```text
FUN_00794a30(...)
  -> FUN_00770e80(&DAT_00c13700, channel_a, channel_b, 0)
```

and the alternate direct caller uses the same outer receiver.

The `DAT_00c13700` symbol denotes address:

```text
0x00c13700
```

### Vehicle-component lane

Phase 633/635/636 establish the separate relation-state path:

```text
FUN_0079a050
  call 0x0079a5bc -> FUN_00757d20
  return 0x0079a5c1
  -> FUN_00757d2c
```

The recovered entry ABI is:

```text
ECX = vehicle pointer
EAX = slot * 0xA80
```

and `FUN_00757d2c` addresses:

```text
vehicle + 0x400 + slot*0xA80
```

The audited runtime callsite supplies the global vehicle object at:

```text
ECX = 0x00c13700
```

Phase 633 separately joins this repeated component layout to the BODY fields
populated by the `FUN_007615c0` vehicle solver setup.

Therefore the two independently recovered pointer lanes meet on the exact same
address:

```text
FUN_00770e80 receiver        = 0x00c13700
runtime vehicle component base = 0x00c13700
```

The composed evidence state is `proven-composed-static`.

## What this corrects

The update batch still produces:

```text
*record + 0x340
```

for `FUN_00794a30`, but the outer call explicitly replaces that receiver with
`&DAT_00c13700` and forwards only the two source-backed 64-bit channel values.

So this phase keeps:

```text
update_child_pointer == global_vehicle_base : unknown
```

while proving:

```text
update_child equality is not required to identify the global vehicle base
```

No pointer inequality is claimed either; the domains are simply not conflated.

## Remaining BODY-pose gate

This proof does **not** prove that the BODY-array owner used by `FUN_007b2270`
is the same pointer domain as `DAT_00c13700`.

The remaining high-value static worklist is now only:

```text
0x00765470  FUN_00765470
0x007b2270  FUN_007b2270
```

Required proof:

```text
DAT_00c13700 / FUN_00770e80
  -> FUN_00765470 receiver/pointer provenance
  -> FUN_007b2270 BODY-array owner
```

Until that edge is closed, the contract deliberately keeps:

```text
global_vehicle_component_base_identity_ready = true
outer_receiver_to_BODY_owner_continuity_proven = false
vehicle_BODY_selection_ready = false
phase698_positive_selection_admissible = false
vehicle_world_transform_ready = false
```

This is narrower than the old three-function `0x713050/0x794a30/0x7615c0`
identity worklist and avoids spending RE effort proving an equality the retail
outer-call ABI does not require.

## Fail-closed checks

The builder rejects:

- recovered-source SHA drift;
- retail PE MD5 drift;
- outer receiver address drift;
- Phase 633/636 call/return/caller drift;
- `FUN_00757d2c` entry ABI drift;
- component base/stride/count drift;
- `FUN_007615c0` layout-anchor drift;
- an input that preclaims update-child equality;
- an input that preclaims global vehicle -> BODY-array owner continuity.

It also cross-checks the committed Phase 635/636 runtime-probe constants rather
than trusting only the new evidence row.

## Next Process 1 action

Audit exact receiver production at the `FUN_00765470 -> FUN_007b2270` boundary.
If that proves the BODY-array owner belongs to the same `0x00c13700` vehicle
physics domain, Process 2 can reassess its Phase 702 continuity gate and admit
the already-proven BMW chassis BODY 0 through Phase 698/700. If it does not,
retain the separate owner domain and follow the exact pointer-producing edge
instead.
