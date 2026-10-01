# Phase 618 — native FUN_007bae40 HINGE projection

Phase 617 ports the single-sample JOINT scalar projection primitive.

Phase 618 ports the next source-backed constraint stage used by
`FUN_007bc680`: one HINGE sample through `FUN_007bae40`.

## Retail source boundary

The retail function is visible directly in the local `SHIFT.exe.c` snapshot at
source line 819157.

Before iterating HINGE samples it prepares:

```text
t = body_axis * L + residual
```

where `L = _DAT_00b8d8c0`.

For each sample:

- scalar base is at `+0x94`;
- side flag is at `+0x98`;
- angular row is `+0x48/+0x50/+0x58`;
- linear row is `+0x60/+0x68/+0x70`;
- nonzero-side transform input is sample `+0x00/+0x08/+0x10`;
- nonzero-side frame offset is sample `+0x78/+0x80/+0x88`;
- sample stride is `0xA0`.

The two source-backed helper boundaries are:

```text
FUN_007aefb0(body + 0xd4, sample_position, transformed)
FUN_007b1320(sample_frame_offset, transformed, cross)
```

`FUN_007b1320` computes:

```text
sample_frame_offset × transformed_sample_position
```

exactly in that order.

## Zero-side branch

When `sample+0x98 == 0`, the kernel writes two positive lanes directly from
the prepared `t` vector and the sample angular/linear rows.

The deterministic regression fixture matches the existing Python oracle:

```text
raw_lanes = [2.94, 5.34]
signed_lanes = [2.94, 5.34]
```

No sample-position transform occurs in this branch.

## Nonzero-side branch

When `sample+0x98 != 0`:

1. sample position is transformed by `FUN_007aefb0`;
2. frame-offset × transformed-position is computed by `FUN_007b1320`;
3. the cross vector is multiplied by `Q = _DAT_00b8d8b8`;
4. the result is added to `t`;
5. the two resulting scalar lanes are subtracted from the BODY solver-vector
   contribution buffer.

For the identity regression fixture:

```text
transformed_sample_position = [1, 2, 3]
cross_vector = [3, 0, -1]
raw_lanes = [6, 0]
signed_lanes = [-6, 0]
```

## Native API

Phase 618 adds:

```text
evaluate_fun_007bae40_hinge()
apply_fun_007bae40_hinge()
```

The evaluator is a single-sample primitive. The apply helper performs the
bounded two-lane write into a neutral solver-vector destination.

Non-finite inputs and out-of-range scalar bases fail closed.

## Regression

`shift_runtime_hinge_projection_check` validates:

- zero-side branch;
- nonzero-side transform branch;
- exact `FUN_007b1320` operand order;
- two-lane sign handling;
- bounded solver-vector writes;
- non-finite rejection.

The checker emits `SHIFT.NativeHingeProjectionCheck/1`.

## Boundary after Phase 618

Phase 618 does not yet iterate the BODY-owned HINGE array and does not complete
`FUN_007bc680`.

Still open:

- native `FUN_007bb090` BAR projection;
- BODY-owned JOINT/HINGE/BAR sample iteration;
- `FUN_007bbb80/FUN_007bb250/FUN_007bb6c0` matrix coupling;
- runtime `FUN_007b3ed0` sampled-state refresh;
- generation of a complete native SBEX contribution frame from these kernels;
- authentic retail runtime contribution evidence.
