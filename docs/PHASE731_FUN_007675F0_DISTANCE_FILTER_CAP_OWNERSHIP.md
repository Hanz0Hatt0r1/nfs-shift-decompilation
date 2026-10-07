# Phase 731 — FUN_007675f0 distance-filter cap ownership

Phase 731 removes `distance_filter_cap` from the production per-pass `FUN_007675f0` provider payload.

## PC retail proof

The already-recovered Phase 379 PC contract records the low-pass update as:

```text
FUN_00783a30(previous, distance, body_field+0xa0, 0.5)
```

So the cap is read from vehicle/object state inside `FUN_007675f0`; it is not a caller-supplied per-pass argument. Phase 731 preserves that ownership distinction without inventing the upstream initializer or a selected-session numeric value.

## Xbox 360 corroboration

The newly available European Xbox 360 `default.xex` was extracted to its inner PowerPC PE and used only as an independent cross-platform oracle. The high-confidence counterpart at `0x8259a9f0`:

- owns the same `+0x4080` filtered distance state topology as PC `FUN_007675f0`;
- reads chassis BODY motion at `BODY+0x78/+0x88`;
- loads `lfd 0,160(r31)` (`+0xa0`) immediately before the corresponding low-pass helper at `0x825b7e10`;
- reads `+0xa0` from the same object base that owns `+0x4080`.

This corroborates the PC ownership result; it does not replace PC offsets or promote Xbox-only semantics into the native contract.

## Native boundary

`Fun007675f0DistanceFilterCapSetup` carries the unresolved `+0xa0` value exactly once. New production callers must supply an explicit finite setup seed. Historical fixtures that return the old complete payload may seed their former `distance_filter_cap` once through compatibility fields.

After setup, both `FUN_0076d100` passes and later session steps reuse the setup-owned value. The per-pass `ContactOuterSessionInput` now contains six production fields:

- `planar_delta`;
- `surface_scalar`;
- `base_scalar`;
- `projected_scalar`;
- `alignment_scalar`;
- `param_3`.

The historical lower `ContactOuterExternalInput` and `ContactOuterKernelInput` retain `distance_filter_cap` because they model the already-frozen lower arithmetic boundary and older standalone fixtures.

## Failure/rollback policy

A missing or non-finite setup seed fails closed. If a historical compatibility seed is admitted during an explicit step or recovered retail batch and a deeper operation throws, the setup admission is rolled back together with the other session transaction state.

## Scope

This phase does **not**:

- guess the `+0xa0` initializer or value;
- claim a physical unit/name for the cap;
- reduce the seven top-level external provider boundaries;
- internalize `planar_delta` or the remaining scalar fields;
- use Xbox evidence as a substitute for PC retail evidence.

The next bounded target is the `planar_delta` producer: PC Phase 379 says `FUN_007675f0` queries `FUN_00759210` using BODY position before constructing the X/Z delta, while the Xbox counterpart mirrors that structure through helper `0x8258ffb8`.
