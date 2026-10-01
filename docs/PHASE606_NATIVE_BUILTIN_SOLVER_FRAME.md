# Phase 606 — prepared native builtin solver frame

Phase 603 ports the source-backed builtin sparse solver `FUN_007b0f20`.
Phase 604 ports the exact builtin diagonal-reset mutation `FUN_007b2210`.
Phase 605 keeps participant-manager and selector identity domains separate.

Phase 606 closes the next safe numerical integration step without inventing a
BMW physics frame.

## Contract

The new preparation contract is:

`SHIFT.NativeBuiltinSolverFrame/1`

implemented by:

`src/physics/native_builtin_solver_frame.py`.

Its source input must be:

`SHIFT.NativeBuiltinSolverFrameInput/1`.

The input is accepted only when all four runtime-only prerequisites are
explicitly true:

- `provider_absent_proven`;
- `matrix_rhs_ready`;
- `reset_selection_ready`;
- `sparse_graph_ready`.

No one of those conditions is derived from static SDF assets.

## Required payload

A prepared frame carries:

- exact square matrix coefficients;
- exact RHS values;
- already-selected reset scalar nodes;
- exact `n+1` forward sparse records;
- exact `n` reverse sparse records;
- verification scope/provenance label.

The Python preparation step validates graph direction/cardinality, applies the
source-backed `FUN_007b2210` reset, then runs the source-backed Python
`FUN_007b0f20` implementation. The resulting solution becomes a numeric
oracle for the native executor.

## Packet

The portable binary packet is:

`SHIFT.NativeBuiltinSolverFramePacket/1`

with magic:

`SBFR`.

It contains, in order:

1. version/cardinality/proof header;
2. row-major float64 matrix;
3. float64 RHS;
4. explicit reset-node indices;
5. variable-length forward sparse graph;
6. reverse sparse graph;
7. Python-reference expected solution.

The packet proof bits are checked again by C++, so bypassing the Python
manifest does not bypass the runtime-evidence gate.

## Native execution

New native API:

- `load_prepared_builtin_solver_frame()`;
- `execute_prepared_builtin_solver_frame()`.

The execution order is fixed:

`FUN_007b2210-equivalent reset → FUN_007b0f20-equivalent solve`.

The native result is compared to the Python-reference oracle with a strict
floating-point tolerance. Any cardinality error, graph error, non-finite value,
zero pivot, incomplete proof mask, trailing packet bytes or oracle mismatch
fails closed.

The standalone executable is:

`shift_runtime_builtin_solver_frame_check`.

It emits:

`SHIFT.NativeBuiltinSolverFrameCheck/1`.

## CLI

Prepare a frame:

```bash
python shift_importer.py native-builtin-solver-frame \
  solver-frame-input.json \
  out/native-solver-frame
```

Execute the native check:

```bash
native_runtime/build/shift_runtime_builtin_solver_frame_check \
  out/native-solver-frame/solver_frame.sbfr
```

## CI boundary

Linux CI uses a synthetic 3-scalar regression frame.

That fixture exists only to verify the handoff/oracle path. It is explicitly
marked `synthetic-regression-fixture` and is not evidence for a retail BMW
frame.

CI also corrupts the packet proof mask and requires the native loader to reject
it.

## What remains open

Phase 606 does not derive or assign:

- retail per-frame matrix/RHS assembly;
- the runtime `sample+0x70 & 1` reset-node selection;
- provider-present dispatch or provider acceptance;
- concrete participant identity;
- `FUN_007b4110` post-solve body-state application;
- execution from the native fixed-step vehicle scheduler.

The next safe native physics step is to admit this prepared frame into the
fixed-step scheduler only when the same provider-absent and participant/runtime
identity evidence is available for that exact frame.
