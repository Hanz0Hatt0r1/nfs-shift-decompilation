# Phase 713 — transactional native fixed step

## Playable-slice blocker removed

The continuous native runtime already carries input, camera double-buffer state,
and persistent BODY feedback across fixed steps. Before Phase 713 a downstream
fail-closed BODY-feedback error could still leave the enclosing native tick
partially committed:

```text
camera begin/swap
  -> PhysicsTickBoundary counters/input mutation
  -> BODY feedback rejects
  -> exception
```

At that point the camera active buffer/counters and physics tick counters could
reflect a tick whose BODY state never committed. That is not a valid persistent
runtime boundary for the first playable Linux slice.

Phase 713 makes the existing native shell fixed step transactional across the
camera and `PhysicsTickBoundary` state that it mutates directly.

## Native order preserved

The successful path remains:

```text
BODY feedback environment admission
  -> runtime boundary validation
  -> camera begin/swap
  -> physics.tick(input)
  -> BODY feedback fixed step
  -> camera complete
```

The phase does not reorder the successful path and does not claim that this
native fixed-step cadence equals the retail outer-update cadence.

Immediately before camera/physics mutation, `NativeRuntimeState::fixed_step()`
retains native snapshots of:

```text
CameraBufferRuntime
PhysicsTickBoundary
```

If a downstream exception escapes the mutation region, both snapshots are
restored and the same exception is rethrown. Therefore a rejected tick does not
consume input counters, advance the native fixed-step count, swap the camera
buffer, or increment camera snapshot/update counters.

`BodyFeedbackScheduler::fixed_step()` already computes the full result into a
local result object before assigning persistent scheduler fields. Phase 713 does
not add a second copy of its potentially large BODY vectors.

## Retry-safe environment admission

Previously `BodyFeedbackScheduler::initialize_from_environment()` latched
`environment_checked=true` before loading the required source contracts. A
missing or invalid evidence path could therefore make a later call return as if
the scheduler had been intentionally disabled.

Phase 713 changes that boundary:

- missing/empty/`0` `SHIFT_NATIVE_BODY_FEEDBACK` is a successful disabled
  admission and latches `environment_checked=true`;
- enabled admission (`1`) keeps `environment_checked=false` while all required
  evidence is loaded and validated;
- `configure()` commits `environment_checked=true` and `enabled=true` only after
  all source contracts are accepted;
- any exception before that point remains retryable after the environment is
  corrected.

## Deliberate non-claims

Phase 713 does **not**:

- schedule any explicit `FUN_00770e80` outer update from `fixed_step()`;
- assert native `1/60` pacing is the retail vehicle cadence;
- internalize any provider whose Process 1 handoff is not positive;
- infer BODY0/VHF bind semantics;
- produce a retail vehicle world transform;
- implement retail camera-follow source/timing semantics;
- change Process 3 resource or Vulkan behavior.

It is strictly a Process 2 runtime integrity change for already existing native
state transitions.

## Regression and CI

The existing C++ regression target
`shift_runtime_body_feedback_scheduler_check` now includes two Phase 713 cases:

1. corrupt the admitted solver topology after configuration so failure occurs
   after camera begin and `physics.tick(input)`; verify the rejected step rolls
   camera/physics counters and input back to the exact pre-step state;
2. enable BODY feedback without the required evidence paths; verify admission
   fails while `environment_checked` remains false and no camera/physics tick is
   committed.

CTest entry:

```text
shift_runtime_body_feedback_scheduler
```

The Python source-contract regression also freezes the rollback statements,
successful call order, retry-safe admission boundary, and the continued absence
of automatic explicit outer-update scheduling inside `fixed_step()`.
