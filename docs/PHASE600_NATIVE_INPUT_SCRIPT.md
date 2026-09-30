# Phase 600 — deterministic native vehicle-control input

Phase 599 makes the recovered CameraManager snapshot/double-buffer boundary live
inside `SHIFT.NativeRuntimeState/1`.

The next native-runtime integration problem is input reproducibility. Keyboard
events already map to the neutral `VehicleControlIntent`, but a CI run cannot
prove that throttle/brake/steer state reached the fixed-step physics boundary
without synthesizing X11 key events.

Phase 600 adds a native-only deterministic input script for that purpose.

## Contract

The script begins with:

```text
SHIFT.NativeRuntimeInputScript/1
```

Each following non-comment row is:

```text
step throttle brake steer_left steer_right
```

Example:

```text
SHIFT.NativeRuntimeInputScript/1
# step throttle brake steer_left steer_right
0 1 0 0 0
1 1 0 0 1
2 0 1 1 0
3 0 0 1 1
4 0 0 0 0
```

All four control values are exact booleans encoded as `0` or `1`.

Rows must be contiguous from step zero. Empty scripts, malformed rows, missing
headers, non-boolean values and oversized scripts fail closed.

## Runtime mode

`native_runtime/shift_runtime` adds:

```text
--input-script FILE
```

When the option is absent, the existing live keyboard mapping remains active.

When it is present:

- X11 is still polled for quit/window events;
- vehicle control state for each fixed step comes from the script;
- every row describes the complete control state for that step;
- if `--frames N` is also supplied, `N` must equal the script row count;
- if `--frames` is omitted, the script row count becomes the run length.

This is explicitly a native deterministic test/control policy. It does not
claim retail controller scheduling, dead zones, analog curves or input
filtering.

## Physics-boundary observability

`PhysicsTickBoundary` now counts the fixed steps for which each neutral intent
bit was active:

- `throttle_steps`;
- `brake_steps`;
- `steer_left_steps`;
- `steer_right_steps`;
- `neutral_input_steps`.

The final `SHIFT.NativeRuntimeFrameLoop/1` report exposes:

- `input_source` = `keyboard` or `script`;
- `input_script_steps`;
- final throttle/brake/left/right state;
- final `vehicle_control_steer_axis`;
- all five activity counters.

The counters are updated inside the same `PhysicsTickBoundary::tick()` that
receives `VehicleControlIntent`. This proves the script is not merely parsed:
the control snapshot crossed the native state boundary.

## Linux CI

The Vulkan workflow runs a five-step input script against the already-prepared
neutral scene set.

Expected activity:

| Intent | Active steps |
|---|---:|
| throttle | 2 |
| brake | 1 |
| steer left | 2 |
| steer right | 2 |
| fully neutral | 1 |

The final step is neutral, so all final boolean controls are false and the
final steer axis is zero.

## Boundary

Phase 600 does not add retail vehicle physics response.

It proves only:

```text
keyboard or deterministic native script
  → VehicleControlIntent
  → SHIFT.NativeRuntimeState/1
  → PhysicsTickBoundary::tick()
```

Gamepad/analog normalization, retail input filtering and force/integration
semantics remain separate evidence/integration tasks.
