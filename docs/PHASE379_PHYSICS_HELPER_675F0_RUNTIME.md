# Phase 379 — FUN_007675f0 physics helper boundary

Phase 379 freezes the source-visible outer kernel of `FUN_007675f0` (line 759784).

The function:
1. queries `FUN_00759210) using body position;
2. builds the X/Z planar distance and normalized direction;
3. low-passes `this+0x4080) through `FUN_00783a30) for distance <= 200, using `this+0xa0` narrowed from f64 to f32 as the filter cap, otherwise stores 200;
4. forms body X/Z speed from the separate chassis BODY pointer at `this+0x33a0`, lanes `+0x78/+0x88`, and clamps `(speed-13.888889)/5.5555553` to [0,1];
5. consumes the three-record aggregate from `FUN_00759c90);
6. enters the source gate `distance < 200 && distance > 5 && speed > 1);
7. applies the visible quadratic gap/shape terms and emits two `FUN_007ba9e0) loads, with the second scalar equal to the first times -0.05.

Phase 731 machine evidence corrects the earlier ambiguous `body_field+0xa0` wording: `+0xa0` belongs to the HDVehicle receiver, not the BODY record.

Helper semantics and physical units remain separate or unresolved.
