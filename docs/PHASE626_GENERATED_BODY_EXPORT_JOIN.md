# Phase 626 — generated BODY contribution → FUN_007ba570 export join

Phase 624 can generate a complete prepared BODY-local `FUN_007bc680`
solver-vector/lower-matrix contribution. Phase 625 can materialize that logical
lower matrix through the source-backed `FUN_007bb8d0`
`BODY+0x154/+0x158/+0x15c` storage contract.

Phase 626 joins those two generated stages directly to the already-native
`FUN_007ba570` export primitive.

## Retail export audit

The retail function at `SHIFT.exe.c:818768` is a pair of linear additive
loops.

It adds:

- the first `BODY+0xa4` doubles from `BODY+0x150` to the global solver
  vector;
- the first `BODY+0xa8` doubles from `BODY+0x154` to the global solver
  matrix.

`FUN_007ba570` does not apply a second row-pointer remap.

That distinction matters: the contribution passed to the native Phase 612
export must be the actual Phase 625 matrix pool, not the Phase 624 logical
matrix view.

## Builtin-layout boundary

In the provider-absent path reconstructed in `FUN_007b3820`, the global
matrix is allocated as N×N doubles with canonical row pointers. The derived
BODY row-index vector is therefore:

```text
row_index[row] = row * N
```

and `BODY+0xa8 = N*N`.

Phase 626 admits only that canonical builtin layout.

It explicitly rejects:

- provider-present storage;
- noncanonical row-index layouts;
- matrix contribution counts other than N².

Phase 625 continues to preserve and validate noncanonical prepared layouts, but
Phase 626 does not claim that those provider-shaped pools can be exported into
the builtin SBFR destination.

## Native API

New files:

- `native_runtime/include/shift_generated_body_solver_export.hpp`;
- `native_runtime/src/generated_body_solver_export.cpp`;
- `native_runtime/tests/generated_body_solver_export_check.cpp`.

`generate_and_export_fun_007bc680_body()` executes:

```text
prepared JOINT/HINGE/BAR samples
  → Phase 624 FUN_007bc680 assembly
  → Phase 625 FUN_007bb8d0 sparse-row materialization
  → PreparedBodySolverContribution shape
  → Phase 612 FUN_007ba570 additive export
```

The result preserves all three intermediate contracts so the checker can prove
that no matrix remap or coefficient change occurs at the handoff.

## Frozen oracle

The Phase 624 six-scalar mixed JOINT/HINGE/BAR fixture is reused unchanged.

Expected generated/exported solver vector:

```text
[7.125, 15.0, 20.3125, 9.125, 20.75, 52.5]
```

Expected canonical 36-double matrix contribution is the same logical
lower-triangle matrix from Phase 624 because canonical row indices are:

```text
[0, 6, 12, 18, 24, 30]
```

The checker requires zero error between:

- Phase 624 generated vector and the exported global vector;
- Phase 625 canonical matrix pool and the exported global matrix;
- the generated contribution and the existing SBEX contribution shape.

It also verifies provider/noncanonical/N² fail-closed gates.

## CI

Linux Vulkan CI runs:

`shift_runtime_generated_body_solver_export_check`

and requires:

- generation function `FUN_007bc680`;
- storage function `FUN_007bb8d0`;
- export function `FUN_007ba570`;
- source line 818768;
- canonical builtin row layout;
- generated contribution/export equality;
- SBEX contribution-shape readiness;
- provider-present and noncanonical-layout rejection;
- maximum oracle error 0.

## Boundary after Phase 626

Phase 626 closes deterministic generation of the BODY-local contribution that
the existing `FUN_007ba570` primitive consumes in the provider-absent builtin
layout.

Still open:

- replacing prepared SBEX evidence with this generated contribution on every
  admitted fixed step;
- authentic `FUN_007b3ed0` sampled-state refresh/input production;
- runtime reset-node selection;
- authentic per-step matrix/RHS/reset observations;
- provider-present export/storage semantics;
- persistent vehicle transform/motion integration.

No new physical units or provider behavior are inferred.
