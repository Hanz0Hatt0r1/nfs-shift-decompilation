# Phase 662 — native FUN_007675f0 outer arithmetic

Phase 662 ports the source-backed outer arithmetic and gate of `FUN_007675f0` into `shift_runtime_physics` as `SHIFT.NativeContactOuterKernel/1`.

The implementation is deliberately narrower than a scheduled contact system. It freezes only arithmetic already captured by the Phase 379 source oracle and keeps caller-side physical naming, record ownership, BODY point submission vectors, and runtime scheduling unresolved.

## Recovered arithmetic

The native kernel preserves the Phase 379 boundaries:

1. X/Z planar distance is `sqrt(dx*dx + dz*dz)` and the corresponding X/Z direction is normalized with Y forced to zero;
2. `FUN_00783a30` is represented by the recovered low-pass expression `(distance - previous) * (response / (cap + response)) + previous`;
3. the caller uses response `0.5` while distance is `<= 200`, otherwise the distance state is set to `200`;
4. body X/Z speed magnitude is `sqrt(vx*vx + vz*vz)`;
5. speed factor is `clamp((speed - 13.888889) / 5.5555553, 0, 1)`;
6. the source gate remains strict: `distance < 200 && distance > 5 && speed > 1`;
7. gap is `distance - (surface_scalar - 1.5)` and the shape is clamped through the recovered `2.5` scale;
8. the visible force scalar is `(base_scalar*1.5 - projected_scalar) * (2-shape) * shape * alignment_scalar * speed_factor`;
9. the two visible submission scales are `force_scalar * param_3` and the first value multiplied by `-0.05`.

Non-finite inputs/results, a zero X/Z normalization path, and a zero `FUN_00783a30` denominator fail closed in the native boundary.

## Deliberately opaque inputs

The names `surface_scalar`, `base_scalar`, `projected_scalar`, `alignment_scalar`, and `param_3` describe their arithmetic role only. This phase does not assign physical units or claim force, tyre, aero, suspension, or surface semantics for those source values.

Likewise `planar_delta` is a source-derived X/Z delta. Its higher-level orientation/provenance is not promoted beyond the Phase 379 arithmetic contract.

## Relationship to Phases 660 and 661

Phase 660 ports the three-record `FUN_00759c90` aggregate and Phase 661 ports recursive `FUN_00759210`. Phase 662 closes the remaining standalone arithmetic/gating portion of their recovered `FUN_007675f0` caller without guessing the still-unresolved caller-side scalar/vector provenance.

The next safe join is to prove the exact mapping from the native Phase 660/661 outputs and other caller intermediates into the Phase 662 scalar inputs, plus the exact two `FUN_007ba9e0` world-point/contribution vectors. Only after that join is source-backed should the contact chain be scheduled by `NativeRuntimeState`.

## Regression

`shift_runtime_contact_outer_kernel_check` covers:

- exact Phase 379 low-pass arithmetic;
- X/Z distance and normalized direction;
- speed-factor lower/upper behavior;
- strict distance/speed gates;
- partial and saturated gap shaping;
- force scalar and paired submission-scale arithmetic;
- distance-state cap above 200;
- zero-path and non-finite rejection.

`native-physics-recent` now executes Phases 656–662.
