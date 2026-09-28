# Phase 421 — SDF provider/backend probe

The runtime capture probe now observes `FUN_007b3f40` before attempting the builtin-solver breakpoint. This closes an important diagnostic hole: a retail frame may use a provider backend, in which case `FUN_007b0f20` is never entered.

## Frame-entry record

At `FUN_007b3f40`, the probe reads the source-backed PhysicsSystem fields:

- `+0x34` — scalar solver count;
- `+0x48` — provider pointer;
- `+0x4c` — solver-state pointer.

A zero provider pointer is recorded as `backend=builtin`; a nonzero pointer is recorded as `backend=provider`. The probe writes `frame_entry_XXXXXX.json` before the solver breakpoint.

The record is diagnostic only. It does not hook or implement the provider vtable. Existing `pre_solve_XXXXXX.json` and `post_solve_XXXXXX.json` formats remain unchanged, so old captures continue to pass through the Phase 416 session bridge.

The vehicle physics profile exposes the same backend-selection contract for static tooling, where the profile defaults to `provider=0` only to describe the builtin-ready branch; it does not claim that the real BMW runtime uses that backend.
