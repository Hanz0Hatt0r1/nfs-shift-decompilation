# Process 1A — `FUN_00713630` PhysicsTweaker materialization

## BLOCKER

After the cadence and participant sample-history paths were closed, P1.1a still required exact ownership of the seven runtime configuration inputs consumed by `FUN_00712940` / `FUN_00713630` and exact adjudication of the apparent `+0x4b0` writer in `FUN_00748280`.

## OUTPUT

`SHIFT.Fun00713630PhysicsTweakerMaterialization/1` proves that the seven apparent globals are fields of one fixed `Physics Tweaker` object rooted at `DAT_00c12c40`.

The retail static initializer at `0x00a8a6f0` loads `ECX=0x00c12c40` and calls `FUN_00748280`. Therefore receiver-relative stores in that constructor are exact fields of `DAT_00c12c40`, not selected-participant state.

The seven inputs map exactly to offsets `+0x2a0/+0x2a4/+0x2a8/+0x2ac/+0x2b0/+0x2b4/+0x2c4`. `FUN_00748280` writes defaults to all seven. `FUN_00749a60` registers the same seven offsets through `FUN_0063a280`. The already-merged source-backed retail cadence contract independently binds the same object to `Physics Tweaker`, `PhysicsTweaker.xml`, and the `FUN_00710a70 -> FUN_0074d400(&DAT_00c12c40)` load path.

This closes owner/default/runtime-registration provenance for the seven configuration inputs without freezing their loaded numeric values or assigning physical semantics.

## `+0x4b0` rejection

The store at `0x00748956` is:

```text
0x00748950 fld  dword [DAT_00b078d4]
0x00748956 fstp dword [ESI+0x4b0]
```

Because the exact constructor root proves `ESI` is the fixed `DAT_00c12c40` PhysicsTweaker object, this store targets `DAT_00c12c40+0x4b0`. It is therefore rejected as a direct writer of the selected participant `+0x4b0` consumed by `FUN_00713630`.

The rejection is based on receiver provenance, not numeric-offset inequality or guessed class semantics.

## GATES_CHANGED

- P1.1a cadence: **closed**.
- P1.1a sample-history scheduling: **closed**.
- P1.1a seven config-field ownership/materialization: **closed**.
- `FUN_00748280+0x4b0` as selected-participant writer: **rejected**.
- actual selected-participant `+0x4b0` writer: **open**.
- P1.1a complete: **false**.
- P1.1 complete: **false**.
- `contact_response` removal: **unauthorized**.
- external provider count: **7**.

## NEXT_STEP

Trace the exact `manager+0x140` record-to-participant construction path. The wrapper record contains the actual participant pointer at `record[0]`; close the writer surface for `+0x4b0` on that exact `0x2b90` participant object, then publish the final Process 1 handoff to Process 2 P2.3.
