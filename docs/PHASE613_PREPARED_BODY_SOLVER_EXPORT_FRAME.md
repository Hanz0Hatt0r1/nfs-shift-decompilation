# Phase 613 — prepared per-BODY solver export frame

Phase 612 ports the exact source-backed `FUN_007ba570` additive transfer from
BODY-local solver contributions into caller-owned global solver buffers.

Phase 613 adds a fail-closed prepared frame around that primitive so a complete
ordered set of explicit BODY contribution values can be replayed natively
without deriving `FUN_007bc680` output from static assets.

## Prepared input

Input format:

`SHIFT.NativeBodySolverExportFrameInput/1`.

The caller must explicitly prove:

- `contribution_values_ready`;
- `body_order_ready`;
- `destination_shape_ready`.

The input contains:

- exact `body_count`;
- exact `solver_scalar_count`;
- contiguous BODY rows in runtime order;
- explicit per-BODY solver-vector contribution arrays;
- explicit per-BODY solver-matrix contribution arrays.

For a scalar count N, the global destinations are exactly:

- N vector doubles;
- N × N matrix doubles.

BODY contribution arrays may be shorter than those destinations, matching the
source-backed count fields at BODY `+0xa4/+0xa8`, but may never exceed them.

## Packet

Builder:

`src/physics/native_body_solver_export_frame.py`.

Output:

- `SHIFT.NativeBodySolverExportFrame/1`;
- packet `SHIFT.NativeBodySolverExportFramePacket/1`;
- magic `SBEX`, version 1.

The packet stores:

1. body/scalar/matrix destination cardinality;
2. proof mask;
3. every BODY row in exact ordinal order;
4. explicit vector/matrix contribution doubles;
5. Python-oracle final global solver vector;
6. Python-oracle final global solver matrix.

The Python oracle starts both global destinations at zero and executes the
existing source-backed `export_body_solver_contributions()` once per BODY.

## Native execution

New native API:

- `load_prepared_body_solver_export_frame()`;
- `execute_prepared_body_solver_export_frame()`.

The loader independently rejects:

- missing proof bits;
- non-contiguous BODY order;
- scalar counts outside the supported range;
- matrix destination sizes other than N²;
- per-BODY contribution counts beyond destination bounds;
- non-finite doubles;
- trailing bytes.

Execution zero-initializes the global destinations and calls the Phase 612
`add_body_solver_contributions()` primitive for each BODY in packet order.
The final vector and matrix must match the packet oracle within the numerical
tolerance.

Standalone verifier:

```bash
native_runtime/build/shift_runtime_body_solver_export_frame_check \
  out/native-body-export/body_solver_export.sbex
```

## CLI

Prepare a frame with:

```bash
python shift_importer.py native-body-solver-export-frame \
  body-export-input.json \
  out/native-body-export
```

The directory contains:

- `body_solver_export.sbex`;
- `body_solver_export_manifest.json`.

## CI

Linux Vulkan CI prepares a synthetic three-BODY / six-scalar frame, executes
the native checker and requires:

- source function `FUN_007ba570`;
- body count 3;
- scalar count 6;
- matrix destination count 36;
- zero native/Python error;
- status `ok`.

A second packet has one proof bit cleared and must fail with
`runtime proofs are incomplete`.

## Boundary after Phase 613

Phase 613 proves ordered native accumulation of explicit BODY contribution
evidence into complete global solver destinations.

It does not derive:

- BODY `+0x150/+0x154` contribution values;
- `FUN_007bc680` projection coefficients;
- `FUN_007b3ed0` sampled-state refresh;
- runtime `sample+0x70 & 1` reset selection;
- provider-present dispatch.

It also does not yet replace the matrix/RHS embedded in
`SHIFT.NativeBuiltinSolverFrame/1`.

The next safe step is an exact join between the Phase 613 resulting global
vector/matrix and the Phase 606/608 prepared builtin solver frame, accepted only
when scalar cardinality and every matrix/RHS double agree.
