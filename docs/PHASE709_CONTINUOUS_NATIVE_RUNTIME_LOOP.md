# Phase 709 — continuous native runtime loop

## Blocker removed

The first playable Linux vertical slice must stay alive as a real interactive
session while preserving native input, persistent BODY feedback, camera state,
and Vulkan submission across successive ticks. Before Phase 709, the vertical
slice simulated this by passing `--frames 2147483647` to a test-oriented bounded
loop. That was operationally long-lived but it was still a synthetic frame-count
sentinel rather than an explicit runtime execution contract.

Phase 709 replaces that sentinel with a Process 2-owned native loop policy:

```text
interactive keyboard profile
  -> --continuous
  -> X11 input/quit polling
  -> NativeRuntimeState::fixed_step()
  -> persistent BODY feedback scheduler
  -> Vulkan frame
  -> next iteration
  -> terminate only on window/quit event
```

`--frames N` remains the bounded deterministic path. When combined with
`--continuous`, an explicitly supplied `--frames N` is only a regression/safety
cap; the interactive vertical-slice launcher does not supply one.

## Scheduling boundary

This phase does **not** claim retail cadence. The runtime continues to execute
one existing native fixed-step boundary per rendered frame and reports:

```text
one-native-fixed-step-per-render-frame-non-retail
```

The existing `camera_schedule = native-fixed-step-non-retail-timing` remains
unchanged. No equality is asserted between the native fixed step and the retail
outer update. Retail cadence remains owned by Process 1 proof.

## Input and fail-closed behavior

Deterministic `SHIFT.NativeRuntimeInputScript/1` playback is finite by contract,
therefore `--continuous` + `--input-script` is rejected. Script cardinality and
explicit `--frames` must still match exactly.

Interactive keyboard mode now emits `frames: null` and
`frame_limit_policy: native-continuous-until-window-quit`; it passes
`--continuous` and no synthetic frame count.

## Regression / CI

`runtime_loop_policy.hpp` is the concrete policy consumed by
`shift_runtime.cpp`. `shift_runtime_loop_policy_check` covers:

- ordinary bounded execution;
- unbounded continuous execution terminated by quit;
- an explicit continuous safety cap for regression use;
- finite scripted execution;
- fail-closed continuous/script incompatibility;
- fail-closed script/frame cardinality mismatch.

CTest registers `shift_runtime_loop_policy`. Python regressions verify that the
vertical-slice launcher consumes the native continuous mode and that the main
runtime loop retains the explicit non-retail scheduling label.

## Remaining blockers

Phase 709 does not promote any Phase 699/708 external provider: `implement_now`
remains zero. It does not fabricate BODY0 bind semantics, drivetrain mapping,
vehicle pose integration, camera-source/controller semantics, or retail game
loop cadence. The next Process 2 integration should consume the first positive
Process 1 producer/bind/scheduling handoff, or another independent proven
runtime blocker.
