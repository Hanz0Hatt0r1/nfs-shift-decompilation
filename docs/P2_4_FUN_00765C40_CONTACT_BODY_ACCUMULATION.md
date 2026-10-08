# Process 2 P2.4 — `FUN_00765c40` contact BODY accumulation

## BLOCKER

The twelve-entry retail contact sweep contains a conditional positive BODY accumulation before the bounded state tail and final optional four-entry sweep. P2.4 must preserve that mutation before removing the top-level `FUN_00765c40` provider.

## INPUT

Process 1 proves that `FUN_007baa70` is called at `0x00766365` on `edi = [HDVehicle+0x33a0]`, selected BODY0. The same Phase 392/native primitive updates angular state as `r x v` and linear state as `v`. The enclosing contact domain is already pinned to twelve ordered slots by `SHIFT.Fun00765c40ContactArraySweepStage/1`.

The exact per-slot branch predicate and producer arithmetic for the two vec3 arguments are not promoted by the current evidence.

## OUTPUT

Adds `SHIFT.Fun00765c40ContactBodyAccumulation/1`.

Native code accepts exactly twelve ordered entries. Each entry carries an explicit source-side `apply` predicate plus source-computed `(point_or_lever_arm, contribution)` vec3 inputs. Slots with `apply=false` are skipped; selected slots invoke the existing native `apply_fun_007baa70_body_accumulator` primitive in retail slot order.

This internalizes the proven BODY mutation surface without guessing the contact acceptance predicate, field semantics, units, or unresolved vector producer formulas.

## GATES_CHANGED

- `0x00766365 -> FUN_007baa70` contact-sweep BODY mutation: native;
- twelve-slot ordering: pinned to the existing contact-array contract;
- per-slot source predicate: remains external;
- per-slot vec3 producer arithmetic: remains external;
- complete `FUN_00765c40`: still incomplete;
- top-level provider: retained;
- external provider count: remains 7.

## TESTS

The focused C++ regression verifies a no-op all-false mask and a deterministic sparse three-slot mask with exact six-channel BODY accumulator output. The Python regression cross-checks evidence, header, docs and stable P2.4 CMake wiring.

## NEXT_STEP

Close the remaining source computations and scheduling used by the residual pass. Remove the top-level `FUN_00765c40` provider only when every required stage can execute end-to-end against native persistent state while retaining the lower scene-query boundary explicitly.
