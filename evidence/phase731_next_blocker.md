# Phase 731 next blocker

Phase 731 moves the PC retail `FUN_007675f0` object field at `+0xa0` out of the production per-pass provider payload and into explicit one-time setup state. No selected value or initializer is inferred.

The next precise Process 2 blocker is the `planar_delta` producer.

PC Phase 379 proves that `FUN_007675f0` first queries `FUN_00759210` using chassis BODY position and then forms the X/Z delta/distance. The Xbox 360 counterpart at `0x8259a9f0` independently mirrors the same structure through helper `0x8258ffb8` before subtracting the BODY origin.

Next work should therefore:

1. identify the exact PC caller/input/output contract of `FUN_00759210`;
2. determine whether its returned point is already derivable from selected-session native state;
3. internalize `planar_delta` only if that producer and freshness/ownership are source-backed;
4. otherwise narrow the producer boundary without assigning physical names or importing Xbox-only semantics.

Do not guess the remaining `surface_scalar`, `base_scalar`, `projected_scalar`, `alignment_scalar`, or `param_3` semantics while resolving this producer.
