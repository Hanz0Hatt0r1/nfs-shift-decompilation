# Phase 714 — continuous persistent BODY state generation

## Playable-slice blocker removed

The native runtime already executes the source-backed provider-absent BODY
feedback solver from every admitted native fixed step. `BodyFeedbackScheduler`
also retained its post-solve `BodyAccumulatorState[]` between calls.

Before Phase 714, however, the runtime had no explicit generation invariant for
that retained state and the regression only proved that two fixed-step calls ran.
It did not fail closed on a stale lineage marker or demonstrate that tick 2
consumed tick 1's committed BODY accumulator output instead of silently
re-seeding from the prepared projection.

Phase 714 closes that Process 2 runtime-integrity blocker:

```text
admitted BODY accumulator seed, generation 0
  -> native fixed step 1
  -> solver/post-solve result
  -> persistent BODY accumulator commit, generation 1
  -> native fixed step 2 consumes generation 1
  -> persistent BODY accumulator commit, generation 2
```

This is the continuous solver-state path only. It does not schedule the explicit
retail outer update and does not promote accumulator state to BODY pose or a
vehicle world transform.

## Runtime invariant

`BodyFeedbackScheduler` now exposes native-only lineage counters:

```text
body_state_generation
last_input_body_state_generation
```

`configure()` admits the prepared source and seeds:

```text
step_count                       = 0
body_state_generation            = 0
last_input_body_state_generation = 0
```

Before any camera or physics mutation, the existing
`validate_runtime_boundary()` requires:

```text
body_state_generation == step_count
bodies.size() == body_count
```

A mismatch fails closed as stale persistent BODY state.

For a successful scheduler step:

1. capture the current `body_state_generation` as the input generation;
2. pass the currently committed `bodies` vector to
   `execute_body_state_feedback_step()`;
3. wait for the complete solver/post-solve result;
4. commit `result.bodies` and solver diagnostics;
5. record the consumed generation;
6. advance exactly one successor generation;
7. set `step_count` equal to the committed generation.

Generation overflow also fails closed instead of wrapping.

## Two-tick regression

The existing `shift_runtime_body_feedback_scheduler_check` C++ regression now
makes the admitted persistent accumulator seed intentionally different from the
immutable prepared `projection.bodies` seed before the first tick.

The established all-reset fixture yields a zero solved vector, so a correct
persistent chain must preserve that admitted value. The regression requires:

```text
step 1 input generation = 0
step 1 output generation = 1
step 1 committed BODY value == admitted persistent seed

step 2 input generation = 1
step 2 output generation = 2
step 2 committed BODY value == step 1 committed BODY value
step 2 committed BODY value != immutable prepared projection seed
```

Therefore a future regression that accidentally reconstructs the second tick
from `projection.bodies` rather than the first tick output fails deterministically.

The regression also corrupts the generation before a tick and verifies rejection
occurs before camera swap or `PhysicsTickBoundary::tick()`. Phase 713's downstream
failure case additionally verifies that a rejected solver step leaves both BODY
generation counters uncommitted.

## Scheduling boundary preserved

Phase 714 deliberately does **not** add any call to:

```text
execute_explicit_outer_update(...)
outer_update.execute(...)
```

inside `NativeRuntimeState::fixed_step()`.

The existing native `1/60` fixed-step remains a host/native scheduling policy.
It is not claimed to equal the retail `FUN_00770e80` outer-update cadence.

Likewise Phase 714 does not:

- synthesize any provider semantics;
- schedule `FUN_007b2270` / `FUN_007bab70` pose integration;
- reinterpret accumulator lanes as position/orientation;
- produce `VehicleWorldMatrix`;
- attach the vehicle transform to the retail camera-follow source;
- change Process 3 resource or Vulkan behavior.

## Regression and CI

Coverage:

```text
native_runtime/tests/runtime_body_feedback_scheduler_check.cpp
tests/test_native_runtime_phase714_continuous_body_state_generation.py
CTest: shift_runtime_body_feedback_scheduler
.github/workflows/native-runtime-phase714.yml
```

The dedicated CI builds the existing scheduler regression, runs its CTest entry,
runs the Phase 713 and Phase 714 source-contract tests together, and verifies the
JSON report contains generation 2 with last input generation 1 after two
successful native fixed steps.

## Remaining blockers

Phase 714 strengthens the already-positive provider-absent continuous solver
path. It does not change the current upstream evidence gates:

```text
retail outer-update fixed-step placement       blocked on Process 1 cadence proof
provider-present producer internalization      blocked on positive Process 1 handoff
outer Vehicle root -> BMW VHF vehicle root    blocked on Process 1 frame proof
retail vehicle-follow camera source/timing     blocked on Process 1 camera proof
```

Until those proofs become positive, Process 2 keeps those production paths
closed.
