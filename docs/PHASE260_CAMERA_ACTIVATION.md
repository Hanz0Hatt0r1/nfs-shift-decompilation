# Phase 260 — Camera activation state transition

Phase 260 reconstructs the control-flow contract of `FUN_0080e1b0`, which is the runtime activation path used after a camera id has been selected.

## Decision sequence

1. `param_2 == -1` makes the effective group selector equal to `param_1`.
2. When an already active group differs from that effective selector, the old group receives the deactivation calls `FUN_0080ce10` / `FUN_0080cdf0`.
3. `param_3 < 0` returns without activating a camera.
4. When the requested camera id already equals the current `+0x26a0` value, the operation is a no-op.
5. Camera lookup goes through `FUN_0080b8e0`; a null result leaves the current camera unchanged.
6. `FUN_004b71f0(camera, 0xc25fb8)` selects the tracking-camera branch. Tracking cameras enter `FUN_0080e0d0` (mode 2); other camera objects enter `FUN_0080e140` (mode 3).
7. `FUN_0080d500` updates the active group/mode state and `+0x26a0` becomes the selected camera id.

`camera_activation_runtime.py` models these observable decisions as a pure state transition. Callback side effects and the RTTI implementation remain external.

## Initial state

`FUN_0080dc60` initializes the camera manager to an inactive state: `+0x26a0` and `+0x26a4` are `-1`, while the other view-management fields receive their executable defaults. The activation contract therefore treats `active_group=-1` and `active_camera_id=-1` as the canonical inactive pair.

## CLI

```json
{
  "active_group": -1,
  "active_camera_id": -1,
  "param_1": 3,
  "param_2": -1,
  "param_3": 7,
  "camera_found": true,
  "is_tracking_camera": false
}
```

```bash
python shift_importer.py camera-activation input.json output.json
```

## Limits

This phase does not synthesize camera transforms, FOV, input processing, look-at behavior or callback implementations. The exact semantic names of the integer group/mode values remain contextual.

Renderer and `RENDER.bff` remain untouched.