# Process 1 — vehicle/BODY identity frontier

Phase 695 already makes persistent BODY pose available to the native runtime:

```text
BODY origin  +0x00/+0x08/+0x10
BODY basis   +0xd4..+0xf4
```

That is not yet a vehicle transform.  The missing Process 1 proof is the static
relationship selecting which BODY belongs to the concrete vehicle/update object.

This stage composes the existing vehicle lifetime, outer-update, persistent
physics and BODY integration contracts without inventing that relationship.
Its purpose is to separate pointer domains that had previously been easy to
conflate.

Tool:

```text
tools/ghidra/build_vehicle_body_identity_frontier.py
```

Output:

```text
SHIFT.VehicleBodyIdentityFrontier/1
```

No original game execution or new runtime capture is used.

## Existing pointer domains

### Persistent lifetime vehicle pointer frontier

`SHIFT.VehicleLifetimeMemoryBridge/1` carries, per verified lifetime descriptor:

```text
vehicle_pointer_function
vehicle_pointer_source_node
stored_table_address
```

This is a persistent lifetime/object frontier.  The same contract deliberately
keeps:

```text
same_runtime_object_as_vehicle_update_proven = false
```

The new identity frontier preserves every such descriptor separately.  It does
not collapse multiple candidates because they share a class-like label, vtable,
allocation helper, or nearby callgraph position.

### Update-child receiver

`SHIFT.OuterUpdateCallsiteStatic/1` proves the source-backed batch topology:

```text
FUN_00713050
record pointer array   this +0x140
record count           this +0x144
record stride          0x1fa0
child receiver         *record +0x340
  -> FUN_00794a30
```

The class identity of the `*record +0x340` child remains unknown.

### Outer physics receiver

The same source/static contract proves that `FUN_00794a30` does **not** use its
caller receiver expression as the receiver of `FUN_00770e80`.

The outer call is source-backed as:

```text
FUN_00770e80(&DAT_00c13700, channel_a, channel_b, mode)
```

The caller object contributes the two 64-bit channel values.  Its receiver
pointer is not syntactically forwarded as the outer-update receiver.

This is a verified pointer-transfer fact.  It is **not** proof that the runtime
numeric value of the update-child pointer can never equal the address of
`DAT_00c13700`; therefore the report explicitly keeps:

```text
runtime_pointer_inequality_between_update_child_and_outer_receiver_proven = false
```

The useful conclusion is narrower: the normal outer call itself is not the
missing vehicle-pointer transport edge.

### BODY-array owner

`SHIFT.BodyFrameIntegrationStatic/1` proves the BODY-array topology used by
`FUN_007b2270`:

```text
owner +0x10   BODY count
owner +0x14   BODY array pointer
stride        0x170
  -> each BODY
  -> FUN_007bab70 persistent origin/basis integration
```

`SHIFT.PersistentVehicleStateClosure/1` places that loop in the proven schedule:

```text
FUN_00770e80
  -> FUN_00765470
      -> ...
      -> FUN_007b2270
          -> FUN_007bab70
```

What is still missing is exact receiver/pointer provenance through
`FUN_00765470` into the owner consumed by `FUN_007b2270`.  Callgraph adjacency
alone is not promoted to same-object identity.

## What this closes

The previous high-level blocker could be read too broadly as:

```text
vehicle object ? BODY object
```

The composed evidence now rejects one misleading route to that proof:

```text
*record +0x340 update-child receiver
  -/-> receiver argument of FUN_00770e80
```

Instead, the normal outer call performs:

```text
update child
  -> two 64-bit channel values
  -> global outer receiver &DAT_00c13700
```

Therefore Process 2 must not select a persistent BODY merely because the vehicle
update path reaches `FUN_00770e80`.

The critical identity blocker is narrowed to:

```text
update_child_receiver
  -> exact BODY index or BODY pointer
  -> BODY[+0x14 + index*0x170]
```

That relationship needs independent static evidence such as a field, registration
call, lifecycle setter, pointer-value transfer, or another exact ownership link.

## Remaining joins

The report separates four remaining questions.

### 1. Lifetime pointer -> update child

Still unknown:

```text
persistent lifetime vehicle pointer
  == / owns / contains
*record +0x340 update child
```

Required evidence must be pointer-value continuity, a proven persistent field,
registration/lifecycle relation, or another independently established ownership
link.  Matching descriptor or table address is insufficient.

### 2. Update child -> BODY index/pointer

This is the highest-priority vertical-slice blocker.

Required evidence:

```text
*record +0x340
  -> BODY index/pointer producer
  -> physics-system BODY array
```

Until it is proven:

```text
vehicle_BODY_selection_ready = false
selected_BODY_index = null
selected_BODY_pointer = null
```

### 3. Outer receiver -> BODY-array owner

The schedule relation is proven, but pointer continuity is not:

```text
&DAT_00c13700
  -> FUN_00770e80
  -> FUN_00765470
  -> ? exact receiver at FUN_007b2270
```

The exact next machine/source target for this sub-boundary is
`FUN_00765470` together with `FUN_007b2270`.

### 4. BODY pose -> vehicle world transform

Phase 695 exposes BODY origin and basis, but Process 1 has not yet proven the
vehicle/world transform convention for the selected concrete BODY.  This stays
blocked behind BODY selection rather than being guessed from matrix layout.

## Next instruction targets

The priority-zero worklist is finite:

```text
FUN_00713050
FUN_00765470
FUN_00794a30
FUN_007b2270
```

They answer two distinct questions:

- `FUN_00713050` / `FUN_00794a30`: find an index/pointer/registration relation
  between the update child and the physics BODY domain;
- `FUN_00765470` / `FUN_007b2270`: prove exact receiver continuity into the BODY
  array owner.

The lifetime `vehicle_pointer_function` targets are retained separately as
priority 1 for joining the persistent create/lifetime object to the update-child
domain.

## Process 2 handoff

A positive `SHIFT.VehicleBodyIdentityFrontier/1` currently means:

```text
persistent BODY pose available                  yes
normal outer call forwards vehicle receiver     no
normal outer call forwards two channel values   yes
vehicle BODY selection ready                    no
vehicle world transform ready                   no
renderer vehicle-transform transport ready      no
```

This is intentionally useful negative evidence.  Process 2 should keep BODY pose
snapshots typed and persistent, but must not bind one to the retail vehicle until
the Process 1 `update child -> BODY index/pointer` join is proven.

## Fail-closed conditions

The builder rejects:

- a lifetime bridge that already claims same-runtime-object update identity;
- outer receiver drift away from `DAT_00c13700`;
- loss of the `*record +0x340` batch child topology;
- first-caller channel-transfer drift;
- persistent schedule-anchor drift;
- any upstream contract that treats matching offsets as object identity;
- BODY count/array/stride drift from `+0x10`, `+0x14`, `0x170`;
- loss of the proven persistent BODY path.

No class name, physical unit, BODY index, world-transform convention, or
render-frame cadence is invented by this layer.
