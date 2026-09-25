# Phase 261 — CameraManager switch-request gate

Phase 261 reconstructs the equality/dirty gate at the beginning of `FUN_0080d3d0`.

## Fast path

A request is considered already current only when all applicable state matches:

- requested mode equals the current mode;
- for mode `1`, the requested sub-index also equals the current sub-index;
- requested sub-flag equals the current sub-flag;
- requested camera id equals the current camera id;
- the camera manager dirty byte at `+0x269d` is clear.

When these conditions hold, `FUN_0080d3d0` returns through its fast path without calling the switch-preparation routine.

## Transition path

When the fast-path conditions fail, the runtime clears `+0x269d`, snapshots the current mode/slot/camera-id fields, and enters `FUN_0080cd40` when the caller requests a switch.

The exact meaning of the integer mode/sub-index fields is deliberately left contextual. The known callers currently expose mode values `1`, `2` and `3`, but this phase does not invent user-facing names for them.

`camera_switch_gate_runtime.py` exposes the gate as a pure function so it can be tested independently of the callback implementations.

## CLI

```json
{
  "state": {"mode": 2, "sub_index": -1, "sub_flag": 0, "camera_id": 7, "dirty": false},
  "requested_mode": 2,
  "requested_sub_index": -1,
  "requested_sub_flag": 0,
  "requested_camera_id": 7
}
```

```bash
python shift_importer.py camera-switch-gate input.json output.json
```

## Limits

No camera transform, callback side effects, or projection behavior is reconstructed here. Renderer and `RENDER.bff` remain untouched.