# Phase 622 — native FUN_007bb250 HINGE↔BAR coupling

Phase 621 ports the HINGE/HINGE self and pair block algebra from
`FUN_007bb250`. Phase 622 closes the remaining mixed HINGE↔BAR block in the
same retail function.

For transformed HINGE angular row A and linear row B, BAR point P and
direction Q, retail evaluates:

```text
d5 = (A.x*P.y - P.x*A.y)*Q.z
   + (A.z*P.x - P.z*A.x)*Q.y
   + Q.x*(P.z*A.y - A.z*P.y)

d6 = (B.x*P.y - P.x*B.y)*Q.z
   + (B.z*P.x - P.z*B.x)*Q.y
   + Q.x*(P.z*B.y - B.z*P.y)
```

The HINGE rows reuse the exact Phase 621 `FUN_007aefb0` float transform
boundary.

Storage policy:

- if `bar_base < hinge_base`: 2×1 block `[[d5],[d6]]` at HINGE rows;
- otherwise: 1×2 block `[[d5,d6]]` at the BAR row;
- equal side flags add;
- differing side flags subtract.

The frozen identity-frame oracle is:

```text
HINGE A=(2,3,4)
HINGE B=(5,6,7)
BAR P=(1,0,2)
BAR Q=(3,4,5)

d5 = 3
d6 = -6
```

## Native implementation

New files:

- `native_runtime/include/shift_hinge_bar_matrix_coupling.hpp`;
- `native_runtime/src/hinge_bar_matrix_coupling.cpp`;
- `native_runtime/tests/hinge_bar_matrix_coupling_check.cpp`.

The checker validates both orientation/sign branches, bounded matrix writes,
range rejection, non-finite rejection and Python/native parity within
`1e-12`.

## Boundary

After Phase 622 all block algebra currently attributed to `FUN_007bb250` is
native: HINGE/HINGE plus HINGE↔BAR.

Still open:

- full HINGE sample-array iteration;
- exact sparse row-pointer orchestration;
- `FUN_007bb6c0` BAR/BAR matrix coupling;
- `FUN_007b3ed0` sampled-state refresh;
- authentic per-step matrix/RHS/reset observations and provider dispatch.

The checker explicitly reports
`full_fun_007bb250_iteration_executed=false`.
