# Phase 620 — native FUN_007bbb80 JOINT matrix coupling

Phases 617–619 close the three independent JOINT/HINGE/BAR projection helpers
used by the `FUN_007bc680` BODY contribution path.

Phase 620 begins the matrix-coupling half with the source-backed
`FUN_007bbb80` JOINT stage.

## Scope

The retail function begins at `SHIFT.exe.c:819720` and iterates the BODY-owned
JOINT array at `+0x160`, stride `0x40`.

This phase ports the exact block algebra independently of the outer sample-array
loop:

- one JOINT self block: 3×3 lower triangle;
- JOINT↔JOINT: 3×3;
- JOINT↔HINGE: 3×2;
- JOINT↔BAR: 3×1;
- equal-side add versus differing-side subtract;
- lower-triangle orientation based on scalar-base ordering.

It does not synthesize runtime JOINT/HINGE/BAR arrays or complete
`FUN_007bbb80` iteration.

## Tensor terms

For one outer JOINT position `(x,y,z)` and the BODY tensor entries consumed by
retail:

```text
a = m00
b = m01
c = m02
d = m11
e = m12
f = m22
```

the recovered intermediates are:

```text
d6  = b*z - c*y
d10 = d*z - e*y
d1  = e*z - f*y
d2  = c*x - a*z
d3  = e*x - b*z
d12 = f*x - e*z
d15 = a*y - b*x
d19 = b*y - d*x
d18 = c*y - e*x
```

The `d15` expression is explicitly frozen as `m00*y - m01*x`. This retains
the earlier source audit that corrected an old accidental `m02` substitution.

## JOINT self block

With BODY inverse scalar `I = BODY+0x90`:

```text
00 = z*d10 - y*d1 + I
10 = z*d3  - y*d12
11 = x*d12 - z*d2 + I
20 = z*d19 - y*d18
21 = x*d18 - z*d15
22 = y*d15 - x*d19 + I
```

Only the lower triangle is stored.

For the identity tensor, `joint=(1,2,3)`, `I=2`, the frozen oracle is:

```text
[00,10,11,20,21,22] = [15,-2,12,-3,-6,7]
```

## Pair blocks

The native port also covers the exact source-backed mixed blocks already frozen
by the Python oracle:

### JOINT↔JOINT

Identity tensor, outer `(1,2,3)`, inner `(4,5,6)`, `I=2`:

```text
[ 30, -8, -12]
[ -5, 24, -15]
[ -6,-12,  16]
```

### JOINT↔HINGE

For HINGE angular `(4,5,6)` and linear `(7,8,9)`:

```text
[ 3,  6]
[-6,-12]
[ 3,  6]
```

### JOINT↔BAR

For BAR point `(4,5,6)`, direction `(7,8,9)`, `I=2`:

```text
[38]
[22]
[ 6]
```

## Storage orientation and sign

Retail stores only the lower triangle through the row-pointer table at
`BODY+0x158`.

For each pair:

- the larger scalar base selects the stored row block;
- the smaller scalar base selects the stored column block;
- reversing base order transposes the algebraic block;
- equal side flags add the block;
- differing side flags subtract it.

Phase 620 preserves that policy explicitly in every native result.

## Native implementation

New files:

- `native_runtime/include/shift_joint_matrix_coupling.hpp`;
- `native_runtime/src/joint_matrix_coupling.cpp`;
- `native_runtime/tests/joint_matrix_coupling_check.cpp`.

The API exposes:

- `derive_fun_007bbb80_joint_tensor_terms()`;
- `evaluate_fun_007bbb80_joint_self()`;
- `evaluate_fun_007bbb80_joint_joint()`;
- `evaluate_fun_007bbb80_joint_hinge()`;
- `evaluate_fun_007bbb80_joint_bar()`;
- `apply_fun_007bbb80_block()`.

All explicit numeric inputs and computed blocks must remain finite.
Block application is bounds-checked.

## CI

`shift_runtime_joint_matrix_coupling_check` is built into
`shift_runtime_physics`, registered in CTest and executed in Linux Vulkan CI.

It verifies:

- all nine tensor intermediates;
- self block;
- both JOINT↔JOINT orientation/sign paths;
- both JOINT↔HINGE orientation/sign paths;
- both JOINT↔BAR orientation/sign paths;
- non-degenerate `d15` source offsets;
- dense destination block application;
- range and non-finite rejection;
- maximum Python/native oracle error ≤ `1e-12`.

## Boundary after Phase 620

The exact JOINT-owned matrix block algebra of `FUN_007bbb80` is now native.

Still open:

- outer JOINT sample-array iteration/orchestration;
- exact sparse row-pointer writes into the runtime solver matrix;
- `FUN_007bb250` HINGE/HINGE + HINGE/BAR coupling;
- `FUN_007bb6c0` BAR/BAR coupling;
- runtime `FUN_007b3ed0` sampled-state refresh;
- authentic per-step matrix/RHS/reset observations;
- provider-present dispatch and persistent vehicle-state integration.
