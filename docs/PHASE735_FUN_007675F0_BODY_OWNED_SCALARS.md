# Phase 735 — FUN_007675f0 BODY-owned scalar ownership

Phase 735 removes the last two directly supplied BODY-derived scalar intermediates from the production `FUN_007675f0` session payload: `base_scalar` and `alignment_scalar`.

PC retail remains authoritative. Exact x86 code in `FUN_007675f0` shows that both values are constructed after the strict outer gate from state already present in the native pass: the probe-derived planar direction, current BODY0 X/Z motion, the persistent filtered-distance state at `HDVehicle+0x4080`, and current `BODY0+0x120`.

## PC provenance

The source-visible sequence at `SHIFT.exe.c:759784` and PC machine code around `0x007677e2..0x0076791f` establish this structure:

1. normalize current BODY0 X/Z motion;
2. cross that direction with source up `[0,1,0]` and normalize the result;
3. if its dot with the probe-derived planar direction is negative, flip the perpendicular vector;
4. use its dot with the planar direction as the scalar later multiplying the visible force expression;
5. form a second perpendicular as `cross([0,1,0], planar_direction)`;
6. dot that vector with current BODY0 X/Z motion, square the result, divide by the current filtered distance state, then multiply by the f32-narrowed value read from `BODY0+0x120`.

The native implementation keeps the historical arithmetic-role names `alignment_scalar` and `base_scalar`. It does not assign a physical interpretation or units.

These calculations are materialized only when the already-recovered outer gate is open:

```text
distance < 200 && distance > 5 && planar BODY0 speed > 1
```

Historical lower-chain fixtures may still provide explicit `base_scalar` and `alignment_scalar`; that path is compatibility only.

## Xbox recomp corroboration

The newly available Xbox recomp makes the cross-platform match substantially easier to verify. The correct counterpart is `sub_825939F0` in `nfs_shift_recomp.223.cpp`, not the previously inspected `sub_8259A978` initializer-neighbor.

The Xbox counterpart independently preserves the same structural offsets:

- vehicle BODY pointer `+0x33a0`;
- persistent distance `+0x4080`;
- BODY X/Z motion `+0x78/+0x88`;
- BODY scalar `+0x120`.

It also preserves the same normalized-motion/perpendicular/sign-alignment/transverse-square topology. Xbox is corroboration and navigation only; PC x86 remains authoritative for the PC runtime and floating-point boundaries.

## Production frontier after Phase 735

Production `ContactOuterSessionInput` now carries only these unresolved caller-side values for this path:

- `surface_probe_node`;
- `projected_scalar`.

`planar_delta`, `surface_scalar`, BODY motion, distance state, distance-filter cap, `param_3`, `base_scalar`, and `alignment_scalar` are no longer supplied as normal per-pass production fields.

`projected_scalar` remains external because its exact upstream `FUN_00759c90` producer join has not yet been closed. The active top-level provider count therefore remains seven.

## Deliberate limits

Phase 735 does not:

- rename either recovered scalar with a physical semantic label;
- claim Xbox floating-point execution is PC-authoritative;
- internalize the `FUN_00759c90` aggregate/record producer;
- close the broader inner conditions and final `FUN_007ba9e0` submission-vector provenance.
