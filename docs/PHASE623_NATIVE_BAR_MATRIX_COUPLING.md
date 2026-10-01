# Phase 623 — native FUN_007bb6c0 BAR/BAR matrix coupling

Phase 623 ports the final independent source-backed matrix primitive used by the
current `FUN_007bc680` reconstruction: BAR/BAR coupling from
`FUN_007bb6c0` at `SHIFT.exe.c:819471`.

## Source-backed math

For BAR point `p` and direction `q`, retail first builds:

```text
cross = p × q
```

and transforms that vector through the exact `FUN_007aefb0(BODY+0xb0, ...)`
float boundary.

Let transformed cross be `l=(lx,ly,lz)` and
`(dx,dy,dz)=q*(BODY+0x90)`.

The self coefficient written to `row_ptr[base][base]` is:

```text
((py*lx - px*ly) + dz) * qz
+ qy * ((px*lz - pz*lx) + dy)
+ qx * ((pz*ly - py*lz) + dx)
```

For an inner BAR sample, retail evaluates:

```text
iqy * ((lz*ix - lx*iz) + dy)
+ iqx * ((ly*iz - iy*lz) + dx)
+ iqz * ((lx*iy - ly*ix) + dz)
```

Equal side flags add; differing flags subtract.

The destination cell is always lower-triangle:

```text
row = max(base_outer, base_inner)
column = min(base_outer, base_inner)
```

## Frozen oracle

Cross/frame case:

```text
body frame = diag(1,2,3)
p = (1,2,3)
q = (4,5,6)

p×q = (-3,6,-3)
M(p×q) = (-3,12,-9)
self coefficient, inverse_scalar=2 = 262
```

Pair case with identity body frame:

```text
outer p=(1,2,3), q=(4,5,6)
inner p=(7,8,9), q=(10,11,12)
inverse_scalar=2

raw pair coefficient = 388
```

## Native implementation

New files:

- `native_runtime/include/shift_bar_matrix_coupling.hpp`;
- `native_runtime/src/bar_matrix_coupling.cpp`;
- `native_runtime/tests/bar_matrix_coupling_check.cpp`.

The native checker validates:

- exact point×direction cross product;
- exact `FUN_007aefb0` float transform boundary;
- self coefficient 262;
- pair coefficient ±388;
- max-base/min-base lower-triangle addressing;
- bounded scalar matrix write;
- range/non-finite rejection;
- Python/native parity within `1e-12`.

## Boundary after Phase 623

All currently recovered independent JOINT/HINGE/BAR projection and matrix-block
algebra is now available in native C++.

Still open:

- BODY-owned JOINT/HINGE/BAR sample-array iteration;
- exact sparse row-pointer orchestration for the full contribution builder;
- joining those generated BODY contributions to the existing Phase 612–615
  export/solver-frame path;
- runtime `FUN_007b3ed0` sampled-state refresh;
- authentic per-step matrix/RHS/reset observations;
- provider-present dispatch and persistent vehicle-state integration.

The checker explicitly reports
`full_fun_007bb6c0_iteration_executed=false`.
