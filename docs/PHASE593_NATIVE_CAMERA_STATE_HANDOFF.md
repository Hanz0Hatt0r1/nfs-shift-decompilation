# Phase 593 — native camera-manager state handoff

The native runtime already carries an evidence-shaped two-buffer
`CameraBufferRuntime`, but until Phase 593 it could only use constructor
defaults. The recovered CameraManager snapshot contract was not connected to
the Linux process.

Phase 593 adds that connection without inventing camera behavior.

## Upstream evidence

`SHIFT.CameraStateSnapshotRuntime/1` models `FUN_0080e040` and preserves the
six manager snapshot words plus active-buffer context:

- opaque camera source/reference;
- manager mode;
- active-buffer sub-index;
- camera id;
- active group;
- group restore value;
- active buffer index;
- active-buffer sub flag.

The retail source pointer is process-local and cannot be reused in the native
process.

## Native contract

New module:

`src/camera/native_camera_state.py`

emits:

`SHIFT.NativeCameraState/1`.

The bridge admits only fields with a portable recovered meaning:

- `active_buffer_index`;
- `manager_mode`;
- `buffer_sub_index`;
- `camera_id`;
- `active_group`;
- `group_restore_value`;
- `active_buffer_sub_flag`.

All signed manager fields are checked against int32 range. The active buffer
must be 0 or 1 and the sub flag must fit one byte.

The contract also freezes the already-recovered `CCameraView` projection
constructor default bits used by `native_runtime`.

## Explicit non-admission

The snapshot's word-0 `camera_source` is recorded only as
`opaque_camera_source_present`.

It is never copied into native state.

The bridge also does not infer:

- inactive camera-buffer contents;
- camera controller behavior;
- camera switch policy;
- tracking/static camera object state;
- camera view matrices or a gameplay target;
- a double-buffer swap event.

Those remain separate runtime/control contracts.

## native_runtime

The Linux runtime adds:

```text
--camera-state FILE
```

where FILE must be a ready `SHIFT.NativeCameraState/1`.

The loader seeds only the declared active camera buffer. The opposite buffer
keeps its native constructor defaults. The runtime does not trigger a camera
buffer swap.

`SHIFT.NativeRuntimeFrameLoop/1` now reports:

- `camera_state_loaded`;
- `camera_state_source`;
- `camera_active_buffer`;
- `camera_manager_mode`;
- `camera_buffer_sub_index`;
- `camera_id`;
- `camera_active_group`;
- `camera_group_restore_value`;
- `camera_active_buffer_sub_flag`;
- `camera_update_in_progress`.

This makes the handoff observable without claiming higher-level camera
execution.

## CLI

Generate the recovered manager snapshot first:

```bash
python shift_importer.py camera-state-snapshot snapshot \
  camera-manager.json \
  out/camera-snapshot.json
```

Then build native input:

```bash
python shift_importer.py native-camera-state \
  out/camera-snapshot.json \
  out/native-camera.json
```

Run:

```bash
native_runtime/build/shift_runtime \
  --bundle out/example-bundle \
  --shader-dir native_runtime/build/shaders \
  --camera-state out/native-camera.json \
  --frames 120
```

## CI checkpoint

Linux Vulkan CI now uses the full two-stage camera bridge and passes the result
to the material-mode runtime smoke.

The final frame-loop report must reproduce the fixture's exact:

- active buffer 1;
- mode 3;
- sub-index 12;
- camera id 8;
- active group 4;
- restore group 6;
- sub flag 1;
- update-in-progress false.

## Boundary after Phase 593

The evidence-backed manager snapshot is now connected to
`SHIFT.NativeRuntimeState/1`.

The next camera work is behavior, not state fabrication: execute proven
double-buffer swap/update events and connect higher-level view/controller
semantics only when their inputs are available.
