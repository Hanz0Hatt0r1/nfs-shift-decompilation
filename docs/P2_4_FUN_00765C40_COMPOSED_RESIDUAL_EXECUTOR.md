# Process 2 P2.4 — composed `FUN_00765c40` residual executor

## INPUT

This slice composes only already-proven native P2.4 stages in the exact order pinned by `SHIFT.Fun00765c40ResidualPassContract/1`.

The selected BMW world position is produced from current BODY bytes. The selected BMW query miss fallback is no longer an explicit composed input: the executor consumes the existing source-backed `SHIFT.Fun00765c40SelectedBMWQueryFallback/1` helper and preserves the retail f32-to-f64 widening exactly. The lower collision implementation remains an explicit `0x00c133ac/+0x1c0` scene-query provider.

The precomputed `FUN_007584f0` interpolation scalar is no longer consumed from the composed input. `SHIFT.Fun007584f0InterpolationCallSeam/2` now receives four positional source arguments and executes the already-native `FUN_00783a30` formula before the persistent `HDVehicle+0x3420` commit. Only the two positive-load qword values in `FUN_007584f0` remain externally produced.

Producer arithmetic that has not yet been reconstructed remains explicit in the composed input structure.

## OUTPUT

Adds the active `SHIFT.Fun00765c40ComposedResidualExecutor/2` contract while retaining `/1` as the historical composed contract.

The executor runs the eleven recovered residual stages in retail order and threads the outputs between them. The contact-array stage is followed by the already-native conditional contact BODY accumulation and bounded state tail before the final optional four-entry BODY sweep.

For `FUN_007584f0`, the result now exposes a native interpolation sub-result in addition to the persistent-write state. A legacy `Fun007584f0ComputedInputs::interpolation_result` field remains available for handoff compatibility, but the composed executor deliberately ignores it and overwrites the local persistent-write input with the native `FUN_00783a30` result.

## GATES_CHANGED

- one end-to-end native orchestration path remains present for the recovered residual pass;
- selected world-position production is native;
- selected BMW `+0x38e8` query fallback materialization is native and no longer caller-supplied to the composed executor;
- `FUN_007584f0 -> 0x00783a30 -> HDVehicle+0x3420` interpolation computation is native inside the composed path;
- the legacy precomputed `FUN_007584f0` interpolation scalar is no longer authoritative in composed execution;
- scene-query invocation and cache/scalar commit are native around the explicit lower collision boundary;
- wheel-state assignment, wheel-job ordering, positive-load count and all previously landed mutation surfaces are composed in one path;
- the two positive-load `FUN_007584f0` qword producers remain explicit and fail-closed;
- other unresolved producer arithmetic remains explicit and fail-closed;
- complete `FUN_00765c40` internalization remains false;
- the top-level `FUN_00765c40` provider remains present;
- external provider count remains 7.

## NEXT STEP

Recover the two positive-load qword producers in `FUN_007584f0` or another independently source-backed residual producer family. Then wire only independently proven families into the promotion path. Remove the top-level `FUN_00765c40` callback only when no unresolved producer dependency remains.
