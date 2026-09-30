# Phase 599 — evidence-backed camera state bridge into native_runtime

The offline Linux runtime has carried a two-buffer camera state shell since the
initial native state milestone, but that shell was initialized only from native
defaults. The recovered CameraManager snapshot/swap contracts were not yet
admitted into it.

Phase 599 closes that transport boundary without implementing unknown camera
source behavior or camera math.

## Source evidence

The bridge reuses SHIFT.CameraStateSnapshotRuntime/1:

- FUN_0080e040 — six-word manager rollback/update snapshot;
- FUN_0080cd40 — guarded active-buffer flip;
- FUN_0080ec80 / FUN_0080e650 — observed update completion sites.

The snapshot contract now explicitly emits status=snapshot; this also fixes the
root camera-state-snapshot snapshot CLI summary path.

## Native bridge contract

New module: src/camera/native_camera_state_bridge.py

It emits SHIFT.NativeCameraStateBridge/1.

The ready bridge carries only fields already recovered as numeric manager/buffer
state:

- native_active_index;
- native_update_in_progress;
- native_manager_mode;
- native_buffer_sub_index;
- native_camera_id;
- native_active_group;
- native_group_restore_value;
- native_active_buffer_sub_flag.

The native_ prefix is intentional: the C++ runtime's minimal JSON reader can
address these top-level fields uniquely without colliding with transition-history
fields.

## Ordered transition validation

A snapshot may be followed by zero or more ordered transition reports.

The bridge validates the recovered state machine:

- swapped must move old_index to exactly 1-old_index, set changed=true, and
  leave the update guard set;
- busy must preserve the active index and report the guard still set;
- ready must complete the currently active index and clear the guard.

Out-of-order or inconsistent transitions block the bridge.

## Opaque camera source

Snapshot word 0 is the runtime camera/source reference. It remains opaque.

Phase 599 records only opaque_camera_source_present=true|false. The value itself
is not serialized into the native ABI and never appears in the bridge output.
No pointer identity, source class, vtable callback, or ownership semantic is
invented.

## Fail-closed fields

A ready native bridge requires a concrete numeric group_restore_value.

The retail snapshot chooses this value through a type-dependent path, so an
unresolved/null value is not replaced with a native default.

All signed manager fields must fit int32; the active buffer is restricted to
0/1 and the sub-flag to one byte.

## native_runtime

native_runtime/shift_runtime adds the optional argument --camera-state FILE.

The file must be a ready SHIFT.NativeCameraStateBridge/1.

CameraBufferRuntime::apply_evidence_snapshot() loads the recovered scalar state
into the final active buffer selected by the bridge and preserves:

- the native recovered projection defaults;
- the other buffer as uninferred/default state;
- the bridge's update-in-progress flag.

The inactive retail camera/static/tracking payload is not synthesized.

## Runtime telemetry

SHIFT.NativeRuntimeFrameLoop/1 now reports:

- camera_state_bridge_loaded;
- camera_active_buffer;
- camera_update_in_progress;
- camera_manager_mode;
- camera_buffer_sub_index;
- camera_id;
- camera_active_group;
- camera_group_restore_value;
- camera_active_buffer_sub_flag.

This makes the transport checkpoint observable without assigning higher-level
camera behavior.

## CLI

Create snapshot/transition reports with camera-state-snapshot, then build the
native bridge with:

    python shift_importer.py native-camera-state-bridge snapshot.json native-camera.json \
      --transition swap.json --transition complete.json

Run the native process with --camera-state native-camera.json.

## Linux CI

The Vulkan workflow constructs a deterministic recovered manager snapshot,
performs one swap and completion, builds the native bridge, then executes the
normal validated material runtime.

The frame-loop result must prove the transported final state:

- active buffer 1;
- update guard clear;
- mode 1;
- sub-index 7;
- camera id 42;
- active group 3;
- restore group 2;
- sub-flag 1.

## Boundary after Phase 599

The camera scalar/double-buffer state transport gate is closed.

Still open:

- camera-source object/vtable execution;
- static/tracking camera payload internals beyond existing recovered contracts;
- view/projection behavior driven by gameplay;
- camera transforms connected to the rendered scene;
- input-driven camera selection/behavior.

Phase 599 does not claim any of those behaviors.
