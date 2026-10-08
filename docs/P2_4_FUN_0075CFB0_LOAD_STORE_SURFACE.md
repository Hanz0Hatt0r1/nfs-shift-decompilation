# Process 2 P2.4 — `FUN_0075cfb0` load-store surface

## BLOCKER

`FUN_00765c40` executes the registered four-wheel job queue before reading each wheel `+0x738` load term. Existing ownership evidence identifies `FUN_0075cfb0` as the registered wheel-job method, but its producer arithmetic and scheduler argument semantics are still unresolved.

The same evidence nevertheless closes a smaller machine-visible surface: retail `FUN_0075cfb0` writes the wheel `+0x738` qword at three exact sites.

## OUTPUT

`SHIFT.Fun0075cfb0LoadStoreSurface/1` owns only that proven commit surface:

- method entry: `0x0075cfb0`;
- initialization store: `0x0075d001`;
- runtime stores: `0x0075ff25`, `0x0075ff3e`;
- per-wheel destination: `wheel+0x738`;
- wheel array: `HDVehicle+0x400`, four elements, stride `0x0a80`;
- corresponding HDVehicle offsets: `+0x0b38`, `+0x15b8`, `+0x2038`, `+0x2ab8`.

The source value is accepted as an opaque `uint64_t` qword and copied bit-for-bit. The API also requires an explicit store-site selector and recovered wheel index.

## FAIL-CLOSED RULES

- wheel index outside `0..3` is rejected;
- store site outside the three recovered machine stores is rejected;
- no finite/range assumption is imposed on the qword payload;
- branch selection is not inferred;
- no source arithmetic is reconstructed.

The native regression deliberately passes NaN-like and all-one qword patterns to prove that this contract is a commit-surface model rather than an invented numerical formula.

## GATES

This slice does **not** close `wheel_job_formula_FUN_0075cfb0` and does not authorize the `WheelJob` producer family in `SHIFT.Fun00765c40ResidualProducerPromotionGate/1`.

The top-level `FUN_00765c40` provider remains present, complete internalization remains false, and external provider count remains **7**.

## NEXT STEP

Recover the branch predicates and arithmetic feeding the three proven `+0x738` stores. Once independent source-backed equivalence exists, Process 2 can authorize the corresponding producer path without widening ownership to unrelated `FUN_0075cfb0` side effects.
