# Process 1A — participant `+0x4b0` writer frontier

## BLOCKER

After cadence, sample-history scheduling, and PhysicsTweaker configuration materialization were closed, P1.1a had one remaining ownership gap: the producer of the selected participant f32 consumed at `participant+0x4b0` by `FUN_00713630`.

## OUTPUT

`SHIFT.Fun00713630Participant4b0WriterFrontier/1` roots the exact participant object and rejects false direct/reflection candidates without assigning semantics.

### Exact selected participant root

`FUN_007125e0` allocates `0x2b90` bytes, constructs the object through `FUN_0072ed20`, and stores the returned pointer in wrapper `record[0]`. The manager wrapper comes from `manager+0x140` with stride `0x1fa0`. The same `record[0]` pointer is later dereferenced by `FUN_00713630`.

`FUN_0072ed20` constructs the relevant polymorphic subobject at `participant+0x340` through `FUN_0079c1c0`, whose final vtable is `0x00b0b744`. Therefore:

```text
participant+0x4b0 == (participant+0x340)+0x170
```

`FUN_007927c0`, on that selected subobject path, directly reads `[subobject+0x170]` at `0x007928d1`.

### Direct surface

The exact subobject constructors `FUN_0079bfd0/FUN_0079c1c0` and the known selected load/update methods checked in the evidence contract contain no direct store to `subobject+0x170`. This does not close computed-offset, escaped-alias, indirect-dispatch, or bulk-copy paths.

### Rejected candidates

- `FUN_00748280 [esi+0x4b0]` is the fixed PhysicsTweaker object `DAT_00c12c40`.
- `FUN_007c3b00 +0x4b0` receives a separately allocated `0x3848` nested object stored at selected subobject `+0x1d00`.
- `FUN_00747c30 +0x170` is rooted by its static initializer to fixed object `0x00c12910`.
- `FUN_007215b0 +0x170` receives `participant+0x2294`, so the write maps to `participant+0x2404`.

### Generic reflection candidate rejected

`FUN_0072a2d0` does register offset `0x170` through `FUN_0063a280`, but the receiver `DAT_00b8d1b4` is a shared registry context with 192 references; this function alone performs 189 registrations across a broad offset table. The exact `0x170` entry carries the string `Add Pressure - Steer From Wall` at `0x00b06630`.

That evidence does not establish object-instance identity with the selected `participant+0x340` subobject or vtable `0x00b0b744`. The branch is therefore rejected as a writer proof rather than promoted from numeric offset equality.

## GATES_CHANGED

- selected participant construction/root identity: **closed**;
- `participant+0x4b0 == subobject+0x170`: **closed**;
- listed false direct candidates: **rejected**;
- generic reflection `+0x170` candidate as identity proof: **rejected**;
- checked constructor/selected-runtime direct store surface: **negative**;
- computed-address / escaped-alias / indirect / bulk materialization: **open**;
- actual participant `+0x4b0` writer: **open**;
- P1.1a/P1.1: **incomplete**;
- external provider count: **7**.

## NEXT_STEP

Continue only with computed-address, escaped-alias, indirect-dispatch, or bulk-copy paths that can be rooted to the exact `participant+0x340` subobject. Do not repeat the closed direct/reflection candidates.
