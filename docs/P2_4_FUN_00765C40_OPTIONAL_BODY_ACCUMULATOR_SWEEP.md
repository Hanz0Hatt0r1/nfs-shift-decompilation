# Process 2 P2.4 — `FUN_00765c40` optional BODY accumulator sweep

## BLOCKER

P2.4 must preserve the complete retail `FUN_00765c40` residual pass before the top-level provider can be removed. The final source-visible stage is an optional four-entry BODY accumulator sweep.

## INPUT

Process 1 already proves:

- the final loop calls `FUN_007baa70` at `0x007664f2`;
- the receiver is `edi = [HDVehicle+0x33a0]`, the selected BODY0;
- the loop has four entries;
- `FUN_007baa70` is the positive Phase 392 BODY accumulator primitive;
- it updates BODY `+0x48/+0x50/+0x58` as `angular += r x v` and `+0x60/+0x68/+0x70` as `linear += v`.

The exact enabling predicate and the producer arithmetic for the two vec3 arguments are not promoted by the current ownership handoff.

## OUTPUT

Adds `SHIFT.Fun00765c40OptionalBodyAccumulatorSweep/1`.

The native stage accepts an explicit `enabled` input plus exactly four `(point_or_lever_arm, contribution)` pairs. Disabled execution preserves BODY state byte-for-byte at the typed state level. Enabled execution applies the existing native `apply_fun_007baa70_body_accumulator` primitive exactly four times in array order.

This makes the proven final BODY mutation executable without inventing the branch predicate, source field names, physical units, or unresolved input formulas.

## GATES_CHANGED

- final four-entry BODY accumulator mutation: native;
- exact `0x007664f2 -> FUN_007baa70` call surface: pinned;
- disabled/enabled behavior: explicit and tested;
- enabling predicate: still external;
- four entry input producers: still external;
- complete `FUN_00765c40`: still incomplete;
- top-level provider: retained;
- external provider count: remains 7.

## TESTS

`shift_runtime_fun_00765c40_optional_body_accumulator_sweep_check` verifies the four-entry count, final-stage ordering, disabled no-op path, and exact six-channel accumulator result on deterministic inputs. The Python regression cross-checks evidence, header and stable P2.4 CMake wiring.

## NEXT_STEP

Internalize the remaining twelve-entry contact-sweep conditional BODY accumulation and any still-external source computations in retail order. Delete the top-level `FUN_00765c40` provider only after the complete pass is executable natively.
