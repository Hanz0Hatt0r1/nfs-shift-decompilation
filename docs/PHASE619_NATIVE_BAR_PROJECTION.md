# Phase 619 — native FUN_007bb090 BAR projection

Phase 618 closes the independent HINGE projection helper in the
`FUN_007bc680` BODY-contribution path. Phase 619 ports the remaining
source-backed scalar projection helper, `FUN_007bb090`, for BAR samples.

## Retail source boundary

The exact function begins at `SHIFT.exe.c:819246`.

One BAR sample has:

- stride `0x60`;
- scalar base at `sample+0x30`;
- side flag at `sample+0x34`;
- nonzero-side bias at `sample+0x38`;
- projection weights at `sample+0x40/+0x48/+0x50`;
- destination `BODY+0x150 + scalar_base*8`.

The BODY/sample cross terms are:

```text
d2 = sample.z * body.axis.y - sample.y * body.axis.z
d3 = body.axis.z * sample.x - sample.z * body.axis.x
d5 = sample.y * body.axis.x - body.axis.y * sample.x
```

The function then evaluates the same three scalar basis expressions that appear
inline in the JOINT projection:

```text
basis.x = (sample.x + body.position.x) * Q
        + (body.correction.x + d2) * L
        + (sample.z*residual.y - sample.y*residual.z)
        + (body.axis.y*d5 - body.axis.z*d3)
        + linear.x

basis.y = (sample.y + body.position.y) * Q
        + (body.correction.y + d3) * L
        + (sample.x*residual.z - sample.z*residual.x)
        + (body.axis.z*d2 - body.axis.x*d5)
        + linear.y

basis.z = (sample.z + body.position.z) * Q
        + (body.correction.z + d5) * L
        + (sample.y*residual.x - sample.x*residual.y)
        + (body.axis.x*d3 - body.axis.y*d2)
        + linear.z
```

BAR reduces them to one scalar:

```text
raw = weight.x*basis.x + weight.y*basis.y + weight.z*basis.z
```

The side rule is distinct from JOINT:

```text
flag == 0: destination += raw
flag != 0: destination -= raw - sample_bias*Q
```

This algebraic basis equality does **not** imply a retail call from
`FUN_007bb090` to `FUN_007bac60`; the BAR function repeats the expressions
inline.

## Python oracle

`src/physics/sdf_constraint_projection_runtime.py` now exposes:

- `evaluate_bar_projection()`;
- `apply_bar_projection()`;
- `describe_bar_projection_provenance()`.

The vehicle physics asset graph now reports
`sdf_bar_projection_ready=true`.

The frozen regression uses the same BODY/sample values as the JOINT oracle:

```text
basis = [9.005, 15.11, 21.515]
weight = [1.1, 1.2, 1.3]
raw = 56.007
```

With `Q=3`, nonzero side and `sample_bias=0.75`:

```text
correction = 2.25
signed lane = -(56.007 - 2.25) = -53.757
```

## Native implementation

New files:

- `native_runtime/include/shift_bar_projection.hpp`;
- `native_runtime/src/bar_projection.cpp`;
- `native_runtime/tests/bar_projection_check.cpp`.

The native API exposes:

- `evaluate_fun_007bb090_bar()`;
- `apply_fun_007bb090_bar()`.

The evaluator preserves the three cross terms, three basis values, raw lane,
side correction and final signed lane. All explicit inputs/outputs must remain
finite. The apply helper writes exactly one solver-vector lane and rejects an
out-of-range scalar base.

## CI

`shift_runtime_bar_projection_check` is linked into
`shift_runtime_physics`, registered with CTest and executed in Linux Vulkan
CI.

CI requires:

- exact function identity `FUN_007bb090`;
- stride 96 and scalar width 1;
- side-bias offset `+0x38`;
- bounded one-lane application;
- range and non-finite rejection;
- oracle error at or below `1e-12`.

## Boundary after Phase 619

The independent JOINT, HINGE and BAR projection primitives used by the
`FUN_007bc680` BODY contribution path are now all source-backed in native C++.

Still open:

- authentic BODY-owned sample iteration/orchestration;
- `FUN_007bbb80` shared JOINT projection/matrix stage;
- `FUN_007bb250` HINGE matrix coupling;
- `FUN_007bb6c0` BAR matrix coupling;
- runtime `FUN_007b3ed0` sampled-state refresh;
- authentic per-step matrix/RHS/reset observations;
- provider-present dispatch and persistent vehicle-state integration.

No physical-unit or coordinate-system interpretation is introduced.
