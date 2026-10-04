# Phase 710 — native continuous fixed-step pacing

## Playable-slice blocker removed

Phase 709 gives the interactive Linux runtime an explicit continuous-until-window-quit loop, but that loop can still advance one nominal `1/60` native fixed step as quickly as Vulkan present returns. On a non-vsynced or software path this makes native physics/camera/input time run faster than wall time.

Phase 710 removes that Process 2 runtime blocker without making any retail scheduling claim:

```text
continuous session
  -> steady_clock host tick
  -> existing native 1/60 fixed-step boundary
  -> input / camera / persistent BODY feedback
  -> solver/contact path already admitted by the runtime
  -> Vulkan frame
  -> next native tick
```

Only `--continuous` is paced. Bounded validation and deterministic input-script playback retain the Phase 709 one-step-per-render behavior so existing regression cardinality stays exact.

## Native policy

`native_runtime/src/runtime_loop_policy.hpp` now carries an explicit continuous host pacing contract:

```text
fixed_tick_seconds = 1 / 60
continuous_wall_clock_pacing = true only for --continuous
clock = std::chrono::steady_clock
wait = std::this_thread::sleep_until
```

The first continuous iteration starts immediately. Later iterations wait until the next host tick when rendering finishes early.

If rendering is late, Phase 710 does not drop or merge native ticks and does not invent a retail catch-up policy. The next deadline advances by exactly one native tick per loop iteration; subsequent iterations therefore run without additional sleep until the host-only schedule catches up.

## Scheduling boundary

This remains a native execution policy, not recovered retail cadence.

The executable still reports:

```text
runtime_loop_schedule = one-native-fixed-step-per-render-frame-non-retail
camera_schedule       = native-fixed-step-non-retail-timing
```

Phase 710 deliberately does **not** attach the explicit deep retail outer update to this clock. It does not claim:

- native `fixed_step` equals retail outer update;
- one rendered frame equals one retail update;
- recovered retail catch-up/drop behavior;
- a Process 1 cadence owner;
- any new provider semantics.

The Phase 699/708 provider frontier therefore remains unchanged with `implement_now = 0`.

## Fail-closed behavior

The continuous pacer rejects a non-positive or below-clock-resolution tick before sleeping. Quit and explicit safety-cap termination are checked before pacing, so an already-ended session does not wait for another tick.

Scripted input remains incompatible with `--continuous` through the Phase 709 policy; no infinite script replay is introduced.

## Regression / CI

The existing native loop regression now verifies:

- bounded and scripted modes do not enable wall-clock pacing;
- continuous mode enables the steady-clock pacer at the existing `1/60` dt;
- a three-tick capped continuous session consumes measurable wall time rather than spinning immediately;
- quit/frame-cap termination remains fail-closed;
- Phase 709 script/cardinality rejection remains intact.

`tests/test_native_runtime_phase710_fixed_step_pacing.py` freezes the source-level boundary that the pacer uses the same `1/60` value as the native runtime and that retail scheduling remains explicitly unclaimed.

## Remaining blockers

Phase 710 improves continuous native execution depth only. The first playable slice still requires the first positive upstream handoff for one or more of:

1. `SHIFT.BMWBody0BindFrameProof/1` for the retail dynamic BMW transform path;
2. one of the nine external vehicle physics producers promoted to `implement_now`;
3. exact retail outer-update cadence ownership;
4. proven input/control producer mapping into drivetrain/wheel state;
5. a source-consistent runtime camera follow source once the persistent vehicle transform is retail-admissible.
