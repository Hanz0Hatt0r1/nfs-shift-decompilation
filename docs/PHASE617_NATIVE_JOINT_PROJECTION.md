# Phase 617 — native FUN_007bac60 JOINT projection

Phase 616 ports the deterministic seed at the front of `FUN_007bc680`:
BODY residual construction, the `FUN_007aefb0` transform and linear-state
scaling.

Phase 617 ports the next retail call in that sequence:

`FUN_007bac60`.

## Source-backed equation

The JOINT sample record uses:

- stride `0x40`;
- scalar base at `sample+0x30`;
- side flag at `sample+0x34`;
- destination `BODY+0x150 + scalar_base*8`.

For body position `b`, body axis `a`, body correction `c`, sample
position `s`, transformed residual `r`, and scaled linear state `l`:

```text
d2 = s.z*a.y - s.y*a.z
d3 = a.z*s.x - s.z*a.x
d5 = s.y*a.x - a.y*s.x

d4 =
  (s.x+b.x)*Q
  + (c.x+d2)*L
  + (s.z*r.y-s.y*r.z)
  + (a.y*d5-a.z*d3)
  + l.x

d6 =
  (s.y+b.y)*Q
  + (c.y+d3)*L
  + (s.x*r.z-s.z*r.x)
  + (a.z*d2-a.x*d5)
  + l.y

d7 =
  (s.z+b.z)*Q
  + (c.z+d5)*L
  + (s.y*r.x-s.x*r.y)
  + (a.x*d3-a.y*d2)
  + l.z
```

`sample+0x34 == 0` adds the three lanes. Any nonzero flag negates them.

The global scales remain the already-recovered initialization:

```text
base = 0.8 * system_value
L = base + base
Q = base * base
```

from `FUN_0070fe90`.

## Native implementation

New files:

- `native_runtime/include/shift_joint_projection.hpp`;
- `native_runtime/src/joint_projection.cpp`;
- `native_runtime/tests/joint_projection_check.cpp`.

The native API exposes:

- `derive_sdf_constraint_scales()`;
- `evaluate_fun_007bac60_joint()`;
- `apply_fun_007bac60_joint()`.

The evaluation step returns:

- `d2/d3/d5`;
- raw `d4/d6/d7`;
- signed lanes.

The application step adds exactly three already-signed lanes at the supplied
scalar base in a BODY-local solver vector and fails closed on an invalid range.

All explicit numeric inputs and outputs must remain finite.

## Oracle parity

The checker reuses the existing Python oracle values from
`tests/test_sdf_constraint_projection_runtime.py`.

The canonical case is:

```text
body_position    = [1, 2, 3]
body_axis        = [0.2, 0.3, 0.4]
body_correction  = [0.5, 0.6, 0.7]
sample_position  = [1.5, 2.5, 3.5]
residual         = [0.1, 0.2, 0.3]
scaled_linear    = [0.4, 0.5, 0.6]
L                = 2
Q                = 3
```

It must produce:

```text
d2/d3/d5 = [0.05, -0.10, 0.05]
lanes     = [9.005, 15.11, 21.515]
```

A nonzero side flag must produce the exact negatives.

The regression also verifies that scalar-base writes touch only the three JOINT
lanes, rejects out-of-range writes and rejects non-finite inputs.

## Oracle correction

Direct re-check of retail `SHIFT.exe.c` at `FUN_007bac60` corrected an
older Python semantic mix-up.

The three cross terms and the matching coupling terms all read BODY
`+0x18/+0x20/+0x28` (the existing `body_axis` field). BODY
`+0x00/+0x08/+0x10` is used only by the `(sample + body_position) * Q`
terms.

Phase 617 updates the Python oracle/evidence and freezes the same offsets in
native C++ before admission.

## Boundary after Phase 617

Phase 617 closes only `FUN_007bac60`.

Still open in the `FUN_007bc680` contribution path:

- `FUN_007bae40` HINGE projection;
- `FUN_007bb090` BAR projection;
- `FUN_007bbb80` shared projection/matrix stage;
- `FUN_007bb250` HINGE coupling;
- `FUN_007bb6c0` BAR coupling;
- the complete runtime BODY `+0x150/+0x154` contribution build.

`FUN_007b3ed0` sampled-state refresh, runtime reset-node selection and
provider-present dispatch remain independent evidence gates.
