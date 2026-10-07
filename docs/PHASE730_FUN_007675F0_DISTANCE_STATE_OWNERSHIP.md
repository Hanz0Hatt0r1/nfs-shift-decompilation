# Phase 730 — FUN_007675f0 persistent distance-state ownership

Phase 730 removes `previous_distance_state` from the production per-pass `FUN_007675f0` input boundary.

PC source evidence at `SHIFT.exe.c:759784` shows that `FUN_007675f0` reads `HDVehicle+0x4080` as the previous value passed to `FUN_00783a30`. When planar distance is at most 200, the filtered result is written back to the same field; when distance exceeds 200, the field is set to 200. Therefore this value is persistent vehicle state, not a value that should be re-supplied by an external provider every pass.

`NativeVehicleProviderSession` now owns that state. Pass 0 consumes the current value and commits the filtered/clamped result before the pass continues; pass 1 consumes pass 0's committed result. The session preserves this state across explicit steps and recovered 180 Hz inner batches.

The upstream initializer for `HDVehicle+0x4080` is not yet proven. New production callers must therefore provide an explicit one-time `Fun007675f0DistanceStateSetup` seed. Historical tests that still return the old complete input may provide their former `previous_distance_state` exactly once through a compatibility-only conversion; that compatibility seed is not retail evidence and is ignored after initialization.

The distance state participates in the same transaction as persistent BODY/projection state: exceptions restore the pre-step state, and failed multi-substep batches restore the pre-batch state.

After Phase 730 the session-facing `ContactOuterSessionInput` has seven still-external production fields: `planar_delta`, `distance_filter_cap`, `surface_scalar`, `base_scalar`, `projected_scalar`, `alignment_scalar`, and `param_3`. The active top-level provider count remains seven.
