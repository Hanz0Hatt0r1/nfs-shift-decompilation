# Phase 729 — FUN_007675f0 BODY0 motion ownership

## Result

Phase 729 narrows the typed external input boundary for the already-native `FUN_007675f0` arithmetic without claiming the remaining caller-side producers.

PC retail evidence establishes that the speed gate reads the current chassis BODY motion lanes at `BODY+0x78` and `BODY+0x88`. `SHIFT.BodyFrameIntegrationStatic/1` separately proves that those persistent BODY lanes are advanced inside each `FUN_00765470` half-step. They therefore belong to native persistent BODY state, not to the session-level `FUN_007675f0` external provider.

The session-facing provider now returns `ContactOuterExternalInput`, retaining only `planar_delta`, `previous_distance_state`, `distance_filter_cap`, `surface_scalar`, `base_scalar`, `projected_scalar`, `alignment_scalar`, and `param_3`. `speed_x` and `speed_z` are absent.

## Per-pass freshness

The BODY motion values are not snapshotted once at the start of `FUN_00770e80`. Phase 729 observes the authoritative persistent BODY bytes immediately before each `FUN_0076d100` anchor sequence. Pass 0 reads the initial BODY0 motion; after the first `FUN_00765470` half-step commits new BODY bytes, pass 1 reads those updated `+0x78/+0x88` values.

A narrow `current_body_observer` bridge is used only to expose the already-owned BODY state at the exact pass boundary. It does not create a new external provider.

## Compatibility and fail-closed behavior

`ContactOuterKernelInput` remains the complete arithmetic input for the Phase 662 kernel and historical fixtures. Compatibility conversion to `ContactOuterExternalInput` deliberately discards legacy `speed_x/speed_z`; production composition re-injects motion only from current BODY0.

The BODY motion decoder rejects malformed/non-`0x170`-multiple buffers, out-of-range reads, non-finite motion lanes, and execution before the current-pass BODY observer has run.

## Scope

The active top-level provider count remains seven. Phase 729 closes only two duplicated `FUN_007675f0` input fields; the other eight caller fields remain external.

Canonical Phase 727 and Phase 728 remain intact: they recover the `FUN_00765c40` world-position transform and the `FUN_007618f0` local query-sample arithmetic. This phase does not replace or reopen either chain.

The next useful target is one of the still-external eight `FUN_007675f0` caller fields, or another surviving provider boundary whose exact producer/ownership can be proven from PC evidence.
