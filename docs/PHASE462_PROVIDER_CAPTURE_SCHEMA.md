# Phase 462 — specialized-provider capture schema

## Goal

Phase 462 introduces a capture format for the provider solver path, separate from the existing builtin SDF solver capture.

The provider path is represented by three raw state regions:

- packed factor workspace doubles;
- static row-pointer table;
- provider output-vector doubles.

## Fixed layouts

Provider 0: 40 scalars, 1190 workspace doubles, workspace base `0x00C21738`, output vector base `0x00C23C68`, solve entry `FUN_007c7200`.

Provider 1: 34 scalars, 746 workspace doubles, workspace base `0x00C1FE38`, output vector base `0x00C21588`, solve entry `FUN_007cdfc0`.

These identities and sizes are the already reconstructed static provider layout; the capture schema does not infer them from runtime values.

## Capture stages

`pre-solve-provider` records the raw provider state before the specialized solve function mutates it.

`post-solve-provider` records the same regions after the solve returns.

The schema intentionally does not force the packed workspace into `SHIFT.SDFSolverCaptureRuntime/1`, because the logical 40×40/34×34 matrix mapping is not yet proven for provider storage.

## Geometry validation

`compare_provider_geometry()` verifies provider id, scalar count, workspace size, and every row-pointer table entry against the static Phase 435 layout.

## Scope boundary

This phase defines the data contract only. The actual debugger hook is a separate step. No provider class name, matrix semantics, physical units, or runtime provider identity is inferred here.
