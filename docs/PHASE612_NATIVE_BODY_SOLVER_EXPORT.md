# Phase 612 — native FUN_007ba570 BODY solver export

Phase 611 keeps the Phase 610 post-solve BODY accumulators alive across native
fixed steps. The next pre-solve gap is the construction of the matrix/RHS that
feeds the builtin solver.

The repository already has a source-backed Python contract for
`FUN_007ba570`. Phase 612 ports that exact primitive operation to native C++
without deriving the contribution values themselves.

## Source-backed operation

For each BODY, `FUN_007ba570` reads two local contribution arrays:

- solver-vector contribution at BODY `+0x150`, count at `+0xa4`;
- solver-matrix contribution at BODY `+0x154`, count at `+0xa8`.

It performs two additive transfers into caller-owned PhysicsSystem buffers:

```text
solver_vector_destination[i] += body_solver_vector[i]
solver_matrix_destination[i] += body_solver_matrix[i]
```

The destination arguments are the buffers associated with PhysicsSystem
`+0x40` and `+0x44` in the recovered call site.

No physical units are assigned to these doubles.

## Native API

New files:

- `native_runtime/include/shift_body_solver_export.hpp`;
- `native_runtime/src/body_solver_export.cpp`.

The exported API is:

`add_body_solver_contributions()`.

It mutates explicit destination buffers in place and returns the two source
counts. Destination buffers shorter than their source contributions fail
closed.

The source function identity is preserved as `FUN_007ba570`.

## Deterministic parity

New executable:

`shift_runtime_body_solver_export_check`.

The regression covers:

1. one BODY vector/matrix additive export;
2. a second BODY export accumulated into the same global destinations;
3. untouched destination tail values;
4. rejection of short destination buffers.

The expected values match the existing Python
`export_body_solver_contributions()` contract.

## Build and CI

`body_solver_export.cpp` is part of `shift_runtime_physics`.

CTest exposes `shift_runtime_body_solver_export`, and Linux Vulkan CI also
runs the checker directly and freezes:

- source function `FUN_007ba570`;
- vector/matrix source counts;
- zero numerical error;
- short-destination rejection.

## Boundary after Phase 612

Phase 612 proves the native additive BODY→global solver-buffer transfer.

It does **not** derive:

- BODY `+0x150/+0x154` contribution values;
- `FUN_007bc680` body constraint projection;
- runtime `FUN_007b3ed0` sampled-state refresh;
- runtime `sample+0x70 & 1` reset selection;
- complete retail matrix/RHS assembly;
- provider-present dispatch.

The next safe integration step is to prepare explicit per-BODY contribution
evidence and execute ordered `FUN_007ba570` accumulation into a complete
40-scalar native solver destination, while keeping contribution generation
itself evidence-gated.
