# Process 1A — `FUN_00713630` participant `+0x4b0` subobject/alias frontier

## BLOCKER

`SHIFT.Fun00713630Participant4b0Frontier/1` bounded the whole retail direct-displacement `+0x4b0` store surface, but the selected participant runtime producer is still open.

## OUTPUT

This contract fixes the exact selected-object alias before continuing the writer search:

```text
actual PhysicsParticipant
  + 0x340 = embedded Vehicle-like subobject constructed by FUN_0079c1c0
  + 0x4b0 = (participant+0x340) + 0x170
```

The subobject receives final vtable `0x00b0b744`. `FUN_007927c0` directly reads `[subobject+0x170]` at `0x007928d1`, so the `FUN_00713630 participant+0x4b0` input and this subobject field are the same storage.

The exact constructors `FUN_0079bfd0/FUN_0079c1c0` and the known selected load/update methods listed in the evidence contain no direct store to `subobject+0x170`. This is a negative direct-surface result only; computed-address, escaped-alias, indirect-dispatch and bulk-copy paths stay open.

Two apparent `+0x170` writers are receiver-rejected:

- `FUN_00747c30` is rooted by its static initializer to fixed receiver `0x00c12910`.
- `FUN_007215b0` receives `participant+0x2294`, so its `+0x170` store maps to `participant+0x2404`, not `participant+0x4b0`.

The reflection candidate is also rejected as identity proof. `FUN_0072a2d0` uses `DAT_00b8d1b4` as a shared registry context, performs 189 `FUN_0063a280` registrations, and its `0x170` entry is named `Add Pressure - Steer From Wall`. Equal numeric offset inside that registry does not establish object-instance identity with `participant+0x340` or vtable `0x00b0b744`.

## GATES_CHANGED

- `participant+0x4b0 == (participant+0x340)+0x170`: **closed**;
- listed false `+0x170` aliases: **rejected**;
- `DAT_00b8d1b4 / +0x170` reflection entry as selected-participant writer proof: **rejected**;
- actual selected-participant runtime producer: **open**;
- P1.1a/P1.1: **incomplete**;
- `contact_response` provider removal: **not authorized**;
- external provider count: **7**.

## NEXT_STEP

Join or reject the remaining direct-displacement `+0x4b0` sites from the current frontier by exact receiver identity. If none survives, inspect only computed-address, escaped-alias, indirect-dispatch and bulk-copy paths rooted to `participant+0x340`.
