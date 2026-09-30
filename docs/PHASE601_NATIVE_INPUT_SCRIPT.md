# Phase 601 — deterministic native vehicle-control input

Phase 600 seeds the recovered CameraManager scalar state into the Phase 599
native snapshot/double-buffer scheduler.

The next native-runtime integration problem is input reproducibility. Live X11
keyboard events already map to the neutral `VehicleControlIntent`, but CI
cannot prove specific throttle/brake/steer sequences reached the fixed-step
physics boundary without synthesizing key events.

Phase 601 adds a native-only deterministic input script for that purpose.

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

All four controls are exact booleans encoded as `0` or `1`.

Rows must be contiguous from step zero. Missing headers, empty scripts,
malformed rows, non-boolean values and oversized scripts fail closed.

## Runtime mode

`native_runtime/shift_runtime` adds:

```text
--input-script FILE
```

When absent, the existing X11 keyboard mapping remains active.

When present:

- X11 still handles quit/window events;
- the script supplies the complete vehicle-control state for every fixed step;
- if `--frames N` is supplied, `N` must exactly equal the script row count;
- without `--frames`, the script length becomes the run length;
- `--camera-state` remains independent and may be used simultaneously.

This is native deterministic test/control infrastructure. It does not claim
retail controller polling cadence, dead zones, analog response curves or input
filtering.

## Physics-boundary observability

`PhysicsTickBoundary::tick()` now counts the steps for which each neutral
intent bit was active:

- throttle;
- brake;
- steer left;
- steer right;
- fully neutral input.

The final `SHIFT.NativeRuntimeFrameLoop/1` report exposes:

- `input_source = keyboard|script`;
- `input_script_steps`;
- final throttle/brake/left/right state;
- final steer axis;
- per-control active-step counters;
- fully-neutral step count.

The counters are updated by the same physics tick that receives
`VehicleControlIntent`. Thus the Phase 601 smoke proves the input crossed
`SHIFT.NativeRuntimeState/1`, not merely that the file parsed.

## Linux CI

The Vulkan workflow reuses the prepared neutral scene set and Phase 600 camera
state bridge, then runs this five-step script:

| Step | Throttle | Brake | Left | Right |
|---:|---:|---:|---:|---:|
| 0 | 1 | 0 | 0 | 0 |
| 1 | 1 | 0 | 0 | 1 |
| 2 | 0 | 1 | 1 | 0 |
| 3 | 0 | 0 | 1 | 1 |
| 4 | 0 | 0 | 0 | 0 |

Expected counts are:

- throttle: 2;
- brake: 1;
- left: 2;
- right: 2;
- neutral: 1.

The final state is neutral and the run length is inferred as five frames.

## Boundary after Phase 601

The native shell now has two input sources that converge on one neutral
vehicle-control boundary:

```text
X11 keyboard
        \
         → VehicleControlIntent
        /
input script
  → SHIFT.NativeRuntimeState/1
  → PhysicsTickBoundary::tick()
```

Still unresolved:

- gamepad/analog normalization;
- retail dead-zone/filtering semantics;
- exact participant/vehicle force application;
- specialized-provider numerical parity.

No retail input or force law is synthesized in this phase.
