# Process 2 P2.4 — `FUN_00765c40` wheel-job scheduling seam

## INPUT

`SHIFT.Fun00765c40LoadTerms/1` proves the retail wheel domain and scheduler boundary:

- four wheel objects at `HDVehicle+0x400`, stride `0x0a80`;
- per-wheel load field `+0x738 f64`;
- queue at `HDVehicle+0x6730`;
- registered wheel job virtual slot `+0x04` resolving to `FUN_0075cfb0`;
- queue execution occurs before `FUN_00765c40` reads the four load terms.

The internal arithmetic of `FUN_0075cfb0` and scheduler argument semantics are not yet natively reconstructed.

## OUTPUT

Adds `SHIFT.Fun00765c40WheelJobScheduling/1`.

The native seam accepts an explicit queue executor and an explicit indexed load-term reader. It executes the queue exactly once, then reads indices 0..3 in order, validates all four values as finite, and returns `Fun00765c40LoadTerms`.

Missing queue/read callbacks are rejected. This keeps the ordering native-owned without falsely claiming the wheel-job formula itself is internalized.

## GATES_CHANGED

- queue-before-load-read ordering: native-owned;
- exactly four post-queue load reads: native-owned;
- finite validation: native-owned;
- `FUN_0075cfb0` producer arithmetic: remains external;
- scheduler argument semantics: remains external;
- complete `FUN_00765c40`: still incomplete;
- top-level provider: retained;
- external provider count: remains 7.

## NEXT_STEP

Recover or natively replace `FUN_0075cfb0` producer arithmetic and compose all P2.4 residual stages into a single end-to-end executor. Remove the top-level `FUN_00765c40` provider only when that composed path no longer depends on it.
