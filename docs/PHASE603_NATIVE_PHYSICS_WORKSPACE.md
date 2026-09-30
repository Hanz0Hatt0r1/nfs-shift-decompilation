# Phase 603 — native SDF workspace materialization

Phase 602 admits the source-backed vehicle participant registry/selector ABI to
the native state while leaving the concrete participant/provider unresolved.

Phase 603 advances the next native-physics boundary without inventing any
force law or provider implementation: it materializes the proven retail logical
solver workspace and executes only the source-backed provider-absent clear
stage.

## Source-backed storage

Phase 484 reconstructed the pre-acceptance allocation in `FUN_007b3820`:

- scalar count at `physics_system+0x34`;
- matrix pool at `+0x38` with
  `scalar_count * scalar_count * 8` bytes;
- 32-bit row-pointer table at `+0x3c` with
  `scalar_count * 4` bytes;
- canonical row pointer:
  `matrix_base + scalar_count * row * 8`.

The solver-frame contract also proves that, when no provider is present,
`FUN_007b3f40` clears:

- the full logical matrix;
- the full RHS vector at `+0x40`.

Body contributions, identity selection, coupling, solve dispatch and post-solve
application occur after that clear stage and remain separate.

## Native representation

`PhysicsWorkspaceBoundary` now owns real storage:

- `matrix_pool: vector<double>`;
- `row_indices: vector<uint32_t>`;
- `rhs: vector<double>`.

The native process is 64-bit, so Phase 603 does not fabricate retail 32-bit
absolute pointers. Instead it preserves the exact row geometry as double
offsets:

`row_indices[row] = scalar_count * row`.

For the admitted BMW 40-scalar domain this produces:

- 1600 matrix doubles;
- 12,800 matrix bytes;
- 40 retail-width row entries / 160 bytes;
- 40 RHS doubles / 320 bytes;
- final row index 1560.

## Fixed-step boundary

When the workspace is materialized and no native provider is bound, every
`PhysicsTickBoundary::tick()` executes the proven provider-absent clear:

1. zero all matrix doubles;
2. zero all RHS doubles;
3. increment `provider_absent_clear_count`.

Phase 603 explicitly keeps:

- `provider_bound = false`;
- `numerical_backend_ready = false`;
- `solver_execution_count = 0`.

No `FUN_007ba2b0` body contribution, JOINT/HINGE/BAR coupling, builtin solve,
provider solve or post-solve application is executed.

## Evidence contract

`src/physics/native_physics_workspace_boundary.py` emits
`SHIFT.NativePhysicsWorkspaceBoundary/1`.

It joins:

- `SHIFT.SpecializedProviderPreAcceptanceMatrixRuntime/1`;
- the retail matrix-storage materializer;
- `SHIFT.SDFConstraintSolverFrameRuntime/2`.

The contract validates the exact matrix/row/RHS sizes and the provider-absent
clear branch.

## Runtime telemetry

`SHIFT.NativeRuntimeFrameLoop/1` now reports:

- `physics_workspace_materialized`;
- `physics_workspace_matrix_doubles`;
- `physics_workspace_row_indices`;
- `physics_workspace_rhs_scalars`;
- matrix / row-table / RHS byte sizes;
- `physics_provider_absent_clears`;
- `physics_provider_bound`;
- `physics_numerical_backend_ready`;
- `physics_solver_execution_count`.

## Linux CI

The neutral scene-set smoke must produce three provider-absent clears for three
fixed steps. The deterministic Phase 601 input script must produce five clears
for five steps.

Both runs must keep numerical backend readiness false and solver execution
count zero.

## Boundary after Phase 603

Native runtime now owns the exact logical storage shape and executes the first
proven per-frame solver stage.

Still unresolved or intentionally disabled:

- BODY contribution materialization in native C++;
- JOINT/HINGE/BAR coupling kernels in native C++;
- runtime identity-reset selector flags;
- builtin numerical solve execution;
- specialized provider selection and execution;
- post-solve application to vehicle body state;
- retail numerical parity.

The next native-physics phase can port a source-backed matrix contribution
stage or builtin solver component, but only where the existing reconstructed
numeric contract is complete enough to test deterministically.
