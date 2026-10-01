# Phase 611 — persistent post-solve BODY accumulator state

Phase 610 proves the prepared provider-absent native chain

`FUN_007b2210 → FUN_007b0f20 → FUN_007b4110`

on every fixed step, but intentionally replays the same prepared BODY input
before each projection.

Phase 611 adds an explicit native-only continuity mode for the six opaque BODY
accumulator channels. It does not promote those channels to vehicle position,
velocity, force, impulse or any other physical unit.

## Runtime option

`native_runtime/shift_runtime` adds:

```text
--persist-post-solve-body-state
```

The option is valid only with `--post-solve-projection`.

Without the option, Phase 610 behavior is unchanged: every fixed step starts
from the BODY state embedded in SBPS.

With the option, the first step starts from that prepared BODY state and each
subsequent fixed step starts from the previous native `FUN_007b4110` output.

## Stateful native API

`execute_post_solve_body_projection_with_state()` accepts:

- the prepared Phase 609 projection contract;
- the actual native solver result;
- an explicit current BODY accumulator vector.

The old `execute_post_solve_body_projection_with_solution()` remains a
compatibility wrapper that supplies the prepared SBPS BODY state.

## Per-step parity

The Phase 609 packet contains a one-step Python oracle. For stateful execution
the native backend derives the proven one-step BODY delta:

`prepared_expected - prepared_initial`.

For every persistent step it requires:

`actual_next - actual_current == prepared_one_step_delta`

within the existing numerical tolerance.

This keeps the source-backed `FUN_007b4110` operator checked on every step
without pretending that the prepared one-step absolute BODY state is valid for
later native steps.

The new result field is `max_delta_error`.

## Deterministic checker

New executable:

```bash
shift_runtime_post_solve_persistence_check post_solve.sbps N
```

It applies the stateful projection N times and proves:

`BODY_N = BODY_0 + N × prepared_delta`.

The checker reports both maximum per-step delta error and final accumulation
error and keeps `persistent_vehicle_state_applied=false`.

## Fixed-step telemetry

`SHIFT.NativeRuntimeFrameLoop/1` adds:

- `physics_post_solve_projection_max_delta_error`;
- `physics_post_solve_persistent_body_state_enabled`;
- `physics_post_solve_persistent_body_state_steps`;
- `physics_solver_persistent_body_accumulator_state_applied`.

The existing
`physics_solver_persistent_vehicle_state_applied=false`
remains unchanged.

## CI

The Phase 610 default run remains and explicitly proves persistence is disabled.

A second five-step run enables `--persist-post-solve-body-state` over the same
40-scalar / 11 BODY / 4 JOINT / 4 HINGE / 20 BAR synthetic evidence. CI
requires five persistent BODY steps, zero solver-vector join error, zero
per-step delta error and persistent BODY accumulator state applied=true while
persistent vehicle state remains false.

The standalone checker also proves five-step linear accumulation.

## Boundary after Phase 611

Phase 611 supplies continuity for the exact BODY accumulator values produced by
the prepared post-solve projection.

It still does not reconstruct:

- retail matrix/RHS assembly;
- runtime reset-node selection;
- runtime JOINT/HINGE/BAR row construction;
- provider-present dispatch;
- conversion of BODY accumulators into persistent rigid-body transform/motion;
- vehicle position/orientation integration.

Those remain independent evidence gates.
