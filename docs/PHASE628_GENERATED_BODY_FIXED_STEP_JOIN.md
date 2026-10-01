# Phase 628 — generated BODY fixed-step solver join

Phase 627 adds `SHIFT.NativeGeneratedBodyConstraintFramePacket/1` (GBCF), a
contribution-free transport for prepared BODY state plus JOINT/HINGE/BAR sample
inputs.

Phase 628 moves that generation path onto every admitted native fixed step.

## Native join

The generated-frame API now exposes:

`verify_generated_body_constraint_frame_matches_builtin_solver_frame()`.

The function:

1. executes the complete Phase 624–627 BODY generation path from GBCF;
2. accumulates generated global solver vector and matrix;
3. validates exact scalar and N² destination shape;
4. compares every generated RHS scalar to the admitted SBFR RHS;
5. compares every generated matrix double to the admitted SBFR matrix;
6. rejects any mismatch before `FUN_007b2210` reset or
   `FUN_007b0f20` solve.

The default tolerance is `1e-12`, matching the existing native BODY/SBFR
equality boundary.

No generated contribution value is stored in GBCF.

## Standalone nonzero oracle

A new native checker is:

`shift_runtime_generated_body_solver_frame_join_check`.

CI reuses the Phase 627 one-BODY, one-JOINT, one-HINGE, one-BAR nonzero GBCF
fixture and joins it to an independently prepared six-scalar SBFR.

Expected generated RHS:

```text
[7.125, 15.0, 20.3125, 9.125, 20.75, 52.5]
```

The complete 36-double Phase 624/626 matrix is also compared exactly.

CI additionally perturbs one SBFR RHS scalar and requires the join to fail with
`generated BODY/RHS join mismatch`.

## Fixed-step runtime mode

`shift_runtime` adds:

```text
--generated-body-constraint-frame FILE.gbcf
```

The option requires `--solver-frame`.

It is mutually exclusive with `--body-solver-export-frame`: the two inputs
represent different pre-solve evidence sources and must not be mixed.

At startup the runtime requires:

- ready participant identity evidence through the existing Phase 607 gate;
- ready physics workspace;
- GBCF scalar count equal to SBFR/workspace scalar count;
- GBCF BODY count equal to workspace BODY count;
- GBCF JOINT and HINGE sample counts equal to
  `workspace.joint_hinge_count`;
- GBCF BAR sample count equal to `workspace.bar_count`;
- an exact generated matrix/RHS → SBFR equality join.

The same generation and equality gate is then executed before every admitted
solver step.

The fixed-step ordering is therefore:

```text
GBCF prepared BODY/sample inputs
  → FUN_007bc680 contribution generation
  → FUN_007bb8d0 BODY matrix storage
  → FUN_007ba570 global matrix/RHS accumulation
  → exact generated matrix/RHS == SBFR gate
  → FUN_007b2210 selected reset
  → FUN_007b0f20 builtin solve
  → optional existing post-solve projection
```

## Runtime telemetry

`SHIFT.NativeRuntimeFrameLoop/1` now exposes:

- `physics_generated_body_constraint_frame_loaded`;
- `physics_generated_body_constraint_body_count`;
- `physics_generated_body_constraint_joint_count`;
- `physics_generated_body_constraint_hinge_count`;
- `physics_generated_body_constraint_bar_count`;
- `physics_generated_body_constraint_join_steps`;
- `physics_generated_body_constraint_native_generation_steps`;
- `physics_generated_body_constraint_max_rhs_join_error`;
- `physics_generated_body_constraint_max_matrix_join_error`;
- `physics_generated_body_constraint_values_stored_in_packet=false`.

The generation-step counter must equal the solver-step counter in the Phase 628
runtime smoke.

## Full-cardinality fixed-step regression

The runtime regression uses the real BMW workspace cardinality:

- 11 BODY;
- 4 JOINT;
- 4 HINGE;
- 20 BAR;
- 40 solver scalars.

The synthetic sample vectors/tensors/scales are zero, so the generated pre-reset
matrix/RHS are exactly zero. All 40 reset rows are selected in the companion
SBFR, making the solve numerically valid while preserving the critical rule:
the GBCF-generated zero matrix/RHS must match the SBFR **before** reset.

This fixture tests scheduler/cardinality/order integration only. The existing
Phase 627 nonzero oracle continues to prove contribution generation arithmetic.

## Boundary after Phase 628

For the provider-absent builtin path, fixed-step execution no longer needs
prepared SBEX contribution values when GBCF is supplied.

Still open:

- authentic `FUN_007b3ed0` sampled-state refresh and GBCF input production;
- runtime reset-node selection from retail `sample+0x70 & 1`;
- provider-present generation/storage/export;
- authentic matrix/RHS/reset observations;
- persistent vehicle transform/motion integration.

The next safe step is to reconstruct or capture the sampled-state refresh that
produces the GBCF inputs rather than preparing them externally.
