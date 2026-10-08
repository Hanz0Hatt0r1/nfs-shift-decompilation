# Process 2 P2.4 — `FUN_007584f0` interpolation call seam

## BLOCKER

The existing `SHIFT.Fun007584f0PersistentWriteStage/1` owns the proven persistent destinations but previously received `HDVehicle+0x3420` as an already-computed float. Process 1 proves the retail coupling: `FUN_007584f0` calls scalar helper `0x00783a30` at `0x007587ef` with four float arguments, then stores its return value at `0x007587f4` into `HDVehicle+0x3420`.

The helper formula is already recovered elsewhere in the native runtime by the Phase 379/662 contract:

```text
(arg1 - arg0) * (arg3 / (arg2 + arg3)) + arg0
```

The semantic names of the four arguments at this specific `FUN_007584f0` call remain unproven, so the caller-side API keeps them positional.

## OUTPUT

`SHIFT.Fun007584f0InterpolationCallSeam/2` owns the proven call/store coupling **and** reuses the existing native `FUN_00783a30` formula:

- helper: `0x00783a30`;
- call site: `0x007587ef`;
- four positional float arguments;
- source-backed scalar formula via `execute_fun_00783a30_distance_filter`;
- one scalar return value, narrowed to float for the persistent store;
- store site: `0x007587f4`;
- destination: `HDVehicle+0x3420`.

No duplicate interpolation implementation is introduced. The existing Phase 379/662 native helper remains the single formula owner.

## FAIL-CLOSED RULES

- positional argument order is preserved;
- the established `FUN_00783a30` finite/denominator checks remain authoritative;
- the helper is executed exactly once per seam invocation;
- the returned float is forwarded into the existing persistent-write stage;
- no physical field name or caller-specific semantic argument name is invented.

## GATES

The scalar-helper portion of `FUN_007584f0_computed_payloads` is now native-owned. The family as a whole remains unresolved because the two positive-load qword producers for `HDVehicle+0x0d40/+0x17c0` are still external.

Therefore no residual-producer promotion bit is set. Complete `FUN_00765c40` internalization remains false, the top-level provider remains present, the lower scene-query provider remains external, and external provider count remains **7**.

## NEXT STEP

Recover the two positive-load qword producers feeding `HDVehicle+0x0d40/+0x17c0`. Once those are independently source-backed, `FUN_007584f0_computed_payloads` can become a candidate for family-level promotion.
