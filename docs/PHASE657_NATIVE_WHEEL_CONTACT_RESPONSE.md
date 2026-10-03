# Phase 657 — native wheel contact response arithmetic

Phase 657 ports the source-backed arithmetic immediately after the recovered wheel collision-query boundary into `shift_runtime_physics`.

## Native boundaries

The implementation exposes the existing retail functions without adding physical names to their opaque fields:

- `FUN_00752f10` packs four curve values as `first`, `width*2`, `pi/width` when `width > 0` (otherwise zero), and `(target-1)/2`;
- `FUN_00755340` evaluates the recovered directional multiplier using `atan2(tangent_x, -tangent_z)`, its strict angular gate and the fourth power of the planar ratio;
- `FUN_007551e0` selects one of three negative/zero or positive 3-vectors per input component, scales each by the squared component and produces the signed three-lane auxiliary result;
- the first `FUN_00766510` stage clamps the query scalar to the observed `[0, limit]` branch sequence and computes `(depth_slope * clamped + base_offset) * directional_factor`.

All inputs and outputs are required to remain finite. No unit labels or tyre-force interpretation are introduced.

## Regression

`shift_runtime_wheel_contact_response_check` mirrors the established Python oracle cases for:

- lower/middle/upper query clamp behavior;
- exact curve packing;
- directional cosine branch and fourth-power ratio;
- zero-vector directional branch;
- sign-selected quadratic response vectors and auxiliary signs;
- the composed `FUN_00766510` response stage;
- fail-closed non-finite input handling.

## Remaining join

The source shows `FUN_00766510` passing `local_200` into `FUN_007551e0`, but the producer of that local vector is not proven at this boundary. Likewise, application to BODY occurs only after additional body-local/world transforms and reaches `FUN_007baa70`, which Phase 656 now provides natively.

Therefore Phase 657 does not guess `local_200`, does not schedule wheel contact response in `NativeRuntimeState`, and does not yet inject the resulting vector into BODY state. Those joins remain evidence-gated.
