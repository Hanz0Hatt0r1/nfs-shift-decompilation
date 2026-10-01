# Phase 618 — native FUN_007bae40 HINGE projection

Phase 617 ports the first constraint helper in the `FUN_007bc680` BODY
contribution path. Phase 618 continues with the source-backed two-lane HINGE
helper `FUN_007bae40`.

## Source-backed equation

The HINGE sample record uses:

- stride `0xA0`;
- scalar base at `sample+0x94`;
- side flag at `sample+0x98`;
- destination `BODY+0x150 + scalar_base*8`.

For BODY axis `axis`, transformed residual `residual`, sample angular/linear
vectors `a` and `b`, and the recovered linear scale `L`:

```text
t = axis * L + residual
c = axis dot (a cross b)
u = axis dot a
v = axis dot b
```

The zero-side branch uses `q = t`. The nonzero-side branch first computes:

```text
position = FUN_007aefb0(body_frame, sample_position)
cross = sample_frame_offset cross position
q = t + Q * cross
```

through source helper `FUN_007b1320`. Both branches then evaluate:

```text
lane0 = a dot q - v * c
lane1 = b dot q + u * c
```

`sample+0x98 == 0` adds both lanes. Any nonzero flag negates them.

## Native implementation

New files:

- `native_runtime/include/shift_hinge_projection.hpp`;
- `native_runtime/src/hinge_projection.cpp`;
- `native_runtime/tests/hinge_projection_check.cpp`.

The native API exposes:

- `evaluate_fun_007bae40_hinge()`;
- `apply_fun_007bae40_hinge()`.

The evaluator retains the base/projected vectors, coupling scalar, axis dot
products, optional transformed position/cross vector, raw lanes and signed
lanes. The nonzero-side branch requires a body frame and reproduces the
`FUN_007aefb0` float matrix/input boundary. The apply helper updates exactly
two already-signed BODY-local solver-vector entries and fails closed on an
invalid range. All explicit numerical inputs and outputs must remain finite.

## Oracle parity

`shift_runtime_hinge_projection_check` covers:

1. the existing Python zero-side oracle `[2.94, 5.34]`;
2. the existing identity-frame nonzero-side oracle `[-6, 0]`;
3. a nontrivial `FUN_007aefb0` transform and `FUN_007b1320` cross product;
4. exact two-lane solver-vector application;
5. invalid scalar-base rejection;
6. missing-frame rejection for the nonzero branch;
7. non-finite input rejection.

Linux CI builds the checker, runs it through CTest, validates its
`SHIFT.NativeHingeProjectionCheck/1` report and requires numerical error at or
below `1e-12`.

## Boundary after Phase 618

Phase 618 closes one HINGE sample independently. It does not synthesize sample
records or claim a complete `FUN_007bc680` BODY contribution.

Still open in that path:

- `FUN_007bb090` BAR projection;
- `FUN_007bbb80` shared projection/matrix stage;
- `FUN_007bb250` HINGE coupling;
- `FUN_007bb6c0` BAR coupling;
- orchestration over authentic BODY/sample arrays;
- runtime `FUN_007b3ed0` sampled-state refresh;
- authentic per-step BODY contribution evidence;
- provider-present dispatch.

No physical unit or coordinate-system interpretation is introduced.
