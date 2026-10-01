# Phase 621 — native FUN_007bb250 HINGE matrix coupling

Phase 620 ports the JOINT-owned matrix block algebra from `FUN_007bbb80`.
Phase 621 continues with the HINGE/HINGE portion of source-backed
`FUN_007bb250` at `SHIFT.exe.c:819302`.

## Scope

One HINGE record uses stride `0xA0`, scalar base `+0x94`, side flag
`+0x98`, and two vector rows at `+0x48` and `+0x60`.

Retail first passes both rows through `FUN_007aefb0(BODY+0xb0, ...)`.
The native port preserves that float matrix/input boundary exactly.

For angular row A, linear row B and transformed rows MA/MB, the self block is:

```text
[base,base]     += A · MA
[base+1,base]   += A · MB
[base+1,base+1] += B · MB
```

The upper off-diagonal entry is not written by this helper.

For outer HINGE i and inner HINGE j:

```text
d5 = A_j · M A_i
d6 = B_j · M A_i
d8 = A_j · M B_i
d7 = B_j · M B_i
```

If `inner_base < outer_base`, retail stores:

```text
[d5 d6]
[d8 d7]
```

at outer rows / inner columns.

Otherwise it stores the transpose:

```text
[d5 d8]
[d6 d7]
```

at inner rows / outer columns.

Equal side flags add; different side flags subtract.

## Native implementation

New files:

- `native_runtime/include/shift_hinge_matrix_coupling.hpp`;
- `native_runtime/src/hinge_matrix_coupling.cpp`;
- `native_runtime/tests/hinge_matrix_coupling_check.cpp`.

The deterministic checker freezes existing Python oracle values:

- diagonal frame diag(1,2,3), A=(1,2,3), B=(4,5,6):
  transformed A=(1,4,9), transformed B=(4,10,18),
  self lower block=(36,78,174);
- identity frame pair:
  raw coefficients d5=50, d6=68, d8=122, d7=167;
- reversed scalar-base order + differing side flags:
  stored block=[[-50,-122],[-68,-167]].

It also verifies bounded 2×2 matrix application and fail-closed range/non-finite
handling at `1e-12` parity tolerance.

## Boundary

Phase 621 closes HINGE/HINGE block algebra only.

Still open:

- HINGE↔BAR coupling inside `FUN_007bb250`;
- full HINGE sample-array iteration;
- exact sparse row-pointer writes;
- `FUN_007bb6c0` BAR/BAR coupling;
- runtime `FUN_007b3ed0` sampled-state refresh;
- authentic per-step matrix/RHS/reset observations and provider dispatch.

The checker explicitly reports
`hinge_bar_coupling_executed=false` and
`full_fun_007bb250_iteration_executed=false`.
