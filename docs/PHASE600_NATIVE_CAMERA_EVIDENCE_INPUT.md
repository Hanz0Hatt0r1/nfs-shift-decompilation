# Phase 600 — recovered camera evidence input for the native scheduler

Phase 599 makes the native fixed-step scheduler execute the recovered
CameraManager six-word snapshot plus guarded double-buffer copy/flip boundary.
That scheduler initially operates on the native constructor/default camera
state.

Phase 600 adds a fail-closed evidence-input path so the same Phase 599
scheduler can start from an externally recovered CameraManager snapshot and
ordered swap/completion state.

## Source contract

The input remains SHIFT.CameraStateSnapshotRuntime/1, reconstructed from:

- FUN_0080e040 — six-word manager snapshot;
- FUN_0080cd40 — guarded buffer flip/copy;
- FUN_0080ec80 / FUN_0080e650 — observed completion sites.

The snapshot form now explicitly emits status=snapshot. This also closes the
existing root camera-state-snapshot snapshot CLI status assumption.

## Native bridge

New module: src/camera/native_camera_state_bridge.py

It emits SHIFT.NativeCameraStateBridge/1.

A ready bridge contains only the recovered numeric subset:

- native_active_index;
- native_update_in_progress;
- native_manager_mode;
- native_buffer_sub_index;
- native_camera_id;
- native_active_group;
- native_group_restore_value;
- native_active_buffer_sub_flag.

Transition reports are applied in order. A swapped row must move to exactly the
opposite buffer with the guard set; busy must preserve the active buffer;
ready must complete the currently active buffer and clear the guard.

Any inconsistent ordering blocks the bridge.

## Opaque word 0 policy

FUN_0080e040 word 0 is the runtime camera/source reference. The Python snapshot
may retain it as an opaque evidence value, but Phase 600 never serializes that
value into the native bridge.

CameraBufferRuntime::apply_evidence_snapshot() explicitly leaves the native
camera source token at zero. No retail pointer/object identity is fabricated.

## Fail-closed scalar policy

The type-dependent group_restore_value must already be numeric. A null or
unresolved value blocks the bridge rather than falling back to the native -1
default.

All manager fields are int32-bounded, active_index is 0/1, and sub_flag is
uint8-bounded.

## native_runtime admission

shift_runtime adds the optional input:

    --camera-state FILE

The file must be a ready SHIFT.NativeCameraStateBridge/1.

Before the frame loop, the bridge initializes the selected active buffer and
guard state. Projection defaults remain the recovered native defaults and the
inactive buffer is not inferred.

The existing Phase 599 fixed-step scheduler then snapshots/copies/flips this
loaded state normally. Phase 600 does not replace that scheduler.

## Runtime telemetry

In addition to the Phase 599 counters, the frame-loop report now exposes:

- camera_state_bridge_loaded;
- camera_manager_mode;
- camera_buffer_sub_index;
- camera_id;
- camera_active_group;
- camera_group_restore_value;
- camera_active_buffer_sub_flag.

Phase 599 camera_snapshot_mode/camera_snapshot_id therefore provide an
independent check that the scheduler actually consumed the loaded evidence.

## Linux CI

The Linux Vulkan workflow builds a deterministic recovered camera snapshot with
mode=1, sub_index=7, camera_id=42, active_group=3, restore_group=2 and
sub_flag=1. It performs one recovered swap and completion, producing final
active_index=1.

The normal validated native material loop then runs 12 steps with that bridge.
CI requires:

- camera_state_bridge_loaded=true;
- final active buffer 1 and guard clear;
- camera_snapshot_count=12 and camera_native_updates=12;
- camera_snapshot_mode=1 and camera_snapshot_id=42;
- all bridged scalar fields unchanged through the scheduler.

## Boundary after Phase 600

Recovered CameraManager scalar state can now seed the live native double-buffer
scheduler.

Still not claimed:

- retail camera-source object identity or vtable behavior;
- exact retail timestamp/update cadence;
- controller behavior and gameplay view-selection policy;
- static/tracking payload internals beyond existing contracts;
- camera/view transform wiring into renderer constants.

The existing Phase 599 schedule label remains
native-fixed-step-non-retail-timing.
