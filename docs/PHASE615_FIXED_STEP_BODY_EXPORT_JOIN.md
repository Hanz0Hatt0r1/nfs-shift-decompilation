# Phase 615 — fixed-step BODY export → solver-frame gate

Phase 614 proves that a prepared BODY export frame can match the pre-reset
matrix/RHS carried by a prepared builtin solver frame.

Phase 615 moves that exact join into the native fixed-step runtime without
claiming that static assets generated the BODY contributions.

## Runtime input

The native runtime adds:

```text
--body-solver-export-frame FILE
```

This option is valid only together with:

```text
--solver-frame FILE
```

The BODY export packet remains `SHIFT.NativeBodySolverExportFramePacket/1`
(SBEX). The solver frame remains
`SHIFT.NativeBuiltinSolverFramePacket/1` (SBFR).

## Verification-only join

Phase 614 exposed one convenience function that verified the join and then ran
the solver.

Phase 615 splits the join into two stages:

`verify_body_export_matches_builtin_solver_frame()`

and the existing:

`join_body_export_to_builtin_solver_frame()`.

The verification-only path:

1. executes the proof-gated ordered `FUN_007ba570` BODY export;
2. checks exact scalar cardinality;
3. compares all exported RHS values with SBFR RHS;
4. compares all N² exported matrix doubles with SBFR matrix;
5. does not run `FUN_007b2210` or `FUN_007b0f20`.

The old Phase 614 helper now reuses that verification and then runs the solver,
so its behavior remains compatible.

## Fixed-step order

When SBEX is supplied, every native fixed step executes the evidence gate before
the existing solver:

```text
prepared BODY contributions
  → FUN_007ba570 replay
  → exact SBEX/RHS + matrix join
  → FUN_007b2210 reset
  → FUN_007b0f20 solve
  → optional FUN_007b4110 post-solve projection
```

A mismatch blocks the runtime before the builtin solve for that step.

## Admission

The runtime rejects:

- SBEX without SBFR;
- SBEX scalar count different from the admitted solver frame;
- invalid/incomplete SBEX proofs;
- any RHS mismatch;
- any matrix mismatch.

The existing workspace and participant-identity gates remain required by SBFR.

## Telemetry

`SHIFT.NativeRuntimeFrameLoop/1` adds:

- `physics_body_solver_export_frame_loaded`;
- `physics_body_solver_export_join_steps`;
- `physics_body_solver_export_max_rhs_join_error`;
- `physics_body_solver_export_max_matrix_join_error`.

A five-step admitted run must report five join steps and zero join error for the
synthetic parity fixture.

## Linux CI

CI derives a 40-scalar SBEX fixture directly from the already prepared
40-scalar SBFR matrix/RHS.

One BODY contribution intentionally covers the complete solver destination.
This is a deterministic evidence fixture, not a retail BODY-count claim.

The existing scripted five-step runtime run now supplies that SBEX and requires
zero RHS/matrix join error on all five steps.

Fail-closed mismatch behavior remains covered by the deterministic Phase 614
join checker, which supplies an independently proof-valid SBEX with one changed
RHS contribution and requires:

`BODY export/RHS join mismatch`.

Phase 615 adds the runtime-specific proof that the same verifier executes on
every admitted fixed step: the five-step run must report five BODY-export join
steps with zero RHS/matrix error.

## Boundary

Phase 615 proves the fixed-step scheduler cannot silently consume prepared SBFR
matrix/RHS that disagree with supplied BODY export evidence.

It still does not derive:

- BODY-local contributions from `FUN_007bc680`;
- runtime sampled constraint state;
- `sample+0x70 & 1` reset-node selection;
- provider-present dispatch;
- physical vehicle-state integration.

Those remain evidence/runtime reconstruction gates.
