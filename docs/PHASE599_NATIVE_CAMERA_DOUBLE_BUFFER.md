# Phase 599 — native camera snapshot/double-buffer integration

The repository already reconstructs the CameraManager state boundaries needed
for a safe native handoff:

- `FUN_0080e040` six-word manager snapshot;
- `FUN_0080cd40` guarded two-buffer flip/copy;
- recovered CameraManager constructor defaults and buffer layout;
- the separate `FUN_0080c920` timestamp/update gate.

Before Phase 599, `SHIFT.NativeRuntimeState/1` only carried a passive
camera-shaped double buffer. The native frame loop did not execute the recovered
snapshot/swap boundary.

Phase 599 connects that boundary without claiming unresolved retail timing or
controller semantics.

## Native state contract

`native_runtime/src/runtime_state.hpp` now contains
`CameraManagerSnapshot` with the exact six-word shape preserved from
`FUN_0080e040`:

1. opaque 32-bit camera-source token;
2. manager mode;
3. active-buffer sub-index;
4. camera id;
5. active group;
6. group restore value.

The camera source remains an opaque 32-bit token. The native runtime does not
dereference it or fabricate a retail object identity.

## Double-buffer update

`CameraBufferRuntime::begin_swap()` keeps the existing guarded behavior and
now:

1. captures the six-word active-manager snapshot;
2. increments native observability counters;
3. copies the active buffer into the opposite buffer;
4. flips `active_index`;
5. raises `update_in_progress`.

`complete_update()` clears the guard.

The native fixed-step boundary calls begin/complete around the existing physics
tick.

This ordering is explicitly a **native scheduler handoff**. It is not a claim
that one 60 Hz native fixed step equals one retail CameraManager timestamp
increment or one exact `FUN_0080c920` invocation.

## Deliberately unresolved timing

Phase 599 does not map:

- the retail `+0x44` timestamp source;
- `FUN_0040f0d0(+0x3c)`;
- the absolute timestamp frequency;
- the retail 0x14 suppression window to native fixed-step units;
- `FUN_0080c510` controller semantics.

Those remain separate source/runtime evidence questions.

## Runtime telemetry

`SHIFT.NativeRuntimeFrameLoop/1` now reports:

- `camera_active_buffer`;
- `camera_update_in_progress`;
- `camera_snapshot_count`;
- `camera_native_updates`;
- `camera_snapshot_mode`;
- `camera_snapshot_id`;
- `camera_schedule = "native-fixed-step-non-retail-timing"`.

This makes the state transition testable without presenting the native schedule
as retail parity.

## Linux CI

The existing three-frame neutral scene-set smoke now requires:

- `camera_snapshot_count = 3`;
- `camera_native_updates = 3`;
- final `camera_active_buffer = 1`;
- `camera_update_in_progress = false`;
- the explicit non-retail scheduling label.

Thus the native shell now exercises the recovered camera snapshot and
double-buffer transition on every native simulation step.

## Boundary after Phase 599

The camera manager snapshot/swap state is now live inside
`SHIFT.NativeRuntimeState/1`.

Still unresolved:

- retail camera update timing;
- camera controller behavior;
- view selection/cycling policy at gameplay level;
- vehicle/target attachment behavior in the native game loop;
- mapping reconstructed view/projection state into exact retail shader constant
  registers.

No render constant register is assigned in this phase.
