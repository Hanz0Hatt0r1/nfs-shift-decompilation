# Phase 629 — native FUN_007b3ed0 constraint sample refresh

Phase 628 removes prepared BODY contribution values from the native fixed-step
path when GBCF is supplied, but GBCF still contains already-refreshed
JOINT/HINGE/BAR sample values.

Phase 629 ports the source-backed refresh stage immediately before
`FUN_007bc680`.

## Retail frame order

Direct audit of `SHIFT.exe.c` recovers:

```text
FUN_007b3f40
  → FUN_007b3ed0 constraint refresh
  → FUN_007bb8d0 per-BODY contribution reset
  → FUN_007bc680 contribution build
  → FUN_007ba570 global export
  → FUN_007b2210 selected scalar reset
  → provider +0x18 or FUN_007b0f20
```

`FUN_007b3ed0` itself iterates exactly three top-level arrays:

| System fields | Record stride | Helper |
|---|---:|---|
| count +0x18 / base +0x1c | 0xA0 | `FUN_007b2da0` |
| count +0x20 / base +0x24 | 0xA0 | `FUN_007b2de0` |
| count +0x28 / base +0x2c | 0xB8 | `FUN_007b2f70` |

Phase 629 preserves that JOINT → HINGE → BAR call order.

## Shared transform boundary

Both refresh and the already-native projection/matrix code use the retail
float-boundary helper `FUN_007aefb0`.

Phase 629 also ports `FUN_007af0a0`, the transposed coefficient order used by
the HINGE negative-side rebuild.

Both helpers:

- accept float32 3×3 BODY frame coefficients;
- cast each source vector component to float32 before multiplication;
- return the three accumulated results as doubles;
- reject non-finite prepared inputs.

No orthonormality or physical-unit interpretation is added.

## JOINT — FUN_007b2da0

The top-level 0xA0 relation record contains BODY/sample pointer pairs at:

- positive BODY +0x78, positive BODY-owned sample +0x7c;
- negative BODY +0x80, negative BODY-owned sample +0x84.

Each BODY-owned JOINT sample is the existing 0x40 record created through
`FUN_007ba8b0`.

Refresh performs only:

```text
sample[+0x18..+0x28] =
    FUN_007aefb0(BODY+0xd4, sample[+0x00..+0x10])
```

for both endpoints.

The resulting +0x18/+0x20/+0x28 triplet is exactly the JOINT position consumed
by `FUN_007bac60` and the Phase 617/624 native path.

## HINGE — FUN_007b2de0

Each BODY-owned HINGE sample is the 0xA0 record created through
`FUN_007ba900`.

Positive-side refresh:

```text
+0x48 = FUN_007aefb0(positive BODY frame, +0x18)
+0x60 = FUN_007aefb0(positive BODY frame, +0x30)
```

Negative-side refresh first transports the positive +0x48 row into negative
BODY-local coordinates:

```text
negative +0x18 =
    FUN_007af0a0(negative BODY frame, positive +0x48)
```

then rebuilds the two local rows exactly as retail:

```text
negative +0x30 = cross(negative +0x00, negative +0x18)
negative +0x18 = cross(negative +0x30, negative +0x00)
```

and finally refreshes:

```text
negative +0x48 = FUN_007aefb0(negative BODY frame, negative +0x18)
negative +0x60 = FUN_007aefb0(negative BODY frame, negative +0x30)
```

The +0x48 and +0x60 rows are exactly the angular/linear vectors consumed by
`FUN_007bae40`, `FUN_007bb250`, and the Phase 618/621–624 native path.

Phase 629 does not rebuild unrelated HINGE static fields such as the position,
frame-offset, scalar base or side flag.

## BAR — FUN_007b2f70

Each BODY-owned BAR sample is the 0x60 record created through
`FUN_007ba990`.

For both endpoints:

```text
sample +0x18 =
    FUN_007aefb0(BODY+0xd4, sample +0x00)
```

Retail then forms:

```text
delta =
    (positive BODY position + positive sample +0x18)
  - (negative BODY position + negative sample +0x18)
```

If `dot(delta, delta) != 0`, it normalizes delta; otherwise it preserves the
zero vector.

The resulting common direction is stored into both endpoint samples at
`+0x40/+0x48/+0x50`.

Those are exactly the BAR direction/weight rows consumed by
`FUN_007bb090`, `FUN_007bb6c0`, and the Phase 619/623/624 native path.

The native implementation uses long-double intermediates for the decompiler's
x87-style norm/sqrt path before storing doubles.

## Native API

New files:

- `native_runtime/include/shift_constraint_sample_refresh.hpp`;
- `native_runtime/src/constraint_sample_refresh.cpp`;
- `native_runtime/tests/constraint_sample_refresh_check.cpp`.

The API exposes:

- `transform_fun_007aefb0_refresh()`;
- `transform_fun_007af0a0_refresh()`;
- `refresh_fun_007b2da0_joint()`;
- `refresh_fun_007b2de0_hinge()`;
- `refresh_fun_007b2f70_bar()`;
- `refresh_fun_007b3ed0_constraints()`.

## Frozen native oracle

The checker covers:

- nontrivial JOINT forward transforms;
- HINGE positive transform, negative transpose transport, cross-product rebuild,
  and final transformed rows;
- BAR endpoint transforms and normalized world direction;
- zero-length BAR delta preservation;
- one JOINT / one HINGE / one BAR `FUN_007b3ed0` ordering/counts;
- non-finite rejection;
- maximum numerical error ≤ `1e-12`.

The checker explicitly reports:

```text
writes_generated_contributions = false
refreshes_prepared_samples = true
```

because this phase stops before GBCF production.

## Boundary after Phase 629

The numerical refresh kernels and array order of `FUN_007b3ed0` are now
native and source-backed.

Still open:

- a transport/ownership contract for the top-level 0xA0/0xA0/0xB8 relation
  records and their BODY-owned sample pointers;
- applying refreshed endpoint values into a generated GBCF before Phase 628;
- authentic per-frame BODY/sample input capture;
- runtime `relation+0x70 & 1` reset-node selection;
- provider-present refresh/generation behavior;
- persistent vehicle transform/motion integration.

The next safe step is the prepared relation-frame transport that joins these
refresh results to the exact BODY/sample identities already carried by GBCF.
