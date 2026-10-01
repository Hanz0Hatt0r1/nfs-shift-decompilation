# Phase 610 — fixed-step solver → post-solve BODY projection join

Phase 608 executes the prepared provider-absent builtin solver frame on the
native fixed-step scheduler. Phase 609 independently ports the exact
`FUN_007b4110` JOINT/HINGE/BAR BODY projection behind a proof-gated SBPS
packet.

Phase 610 joins those two boundaries without deriving any retail-only input.

## Runtime option

`native_runtime/shift_runtime` adds:

```text
--post-solve-projection FILE
```

The option is valid only together with `--solver-frame`.

## Admission gates

A Phase 609 projection is admitted on the fixed-step path only when:

1. the Phase 608 solver-frame path is already ready;
2. runtime participant identity remains proven;
3. the SBPS solved-vector cardinality equals the solver-frame scalar count;
4. SBPS BODY count equals the native physics workspace BODY count;
5. SBPS JOINT and HINGE counts each equal the workspace `joint_hinge_count`;
6. SBPS BAR count equals the workspace `bar_count`;
7. the Phase 609 packet proof mask is complete.

For the BMW manifest this means exactly 11 BODY, 4 JOINT, 4 HINGE, 20 BAR and
40 solver scalars.

## Per-step execution

Each admitted fixed step now performs:

```text
FUN_007b2210
  → FUN_007b0f20
  → actual solver_result.solution
  → Phase 610 solved-vector identity join
  → FUN_007b4110
```

The post-solve executor does not trust the solved vector duplicated inside
SBPS. The actual native solver result is supplied explicitly to the Phase 609
executor. Every scalar must match the prepared SBPS vector within the same
fail-closed numerical tolerance before any BODY projection is accepted.

The existing Phase 609 Python oracle still validates every final BODY channel.

## Telemetry

`SHIFT.NativeRuntimeFrameLoop/1` adds:

- `physics_post_solve_projection_loaded`;
- `physics_post_solve_projection_body_count`;
- `physics_post_solve_projection_joint_count`;
- `physics_post_solve_projection_hinge_count`;
- `physics_post_solve_projection_bar_count`;
- `physics_post_solve_projection_steps`;
- `physics_post_solve_projection_max_solver_join_error`;
- `physics_post_solve_projection_max_oracle_error`.

`physics_solver_post_solve_body_state_applied=true` now means the prepared
FUN_007b4110 projection executed after the native solver on every completed
solver step.

`physics_solver_persistent_vehicle_state_applied=false` remains explicit:
Phase 610 replays the prepared BODY state for evidence/parity and does not yet
feed the projected accumulators into persistent vehicle motion/integration.

## CI

The existing synthetic 40-scalar Phase 608 frame is reused. CI reads its
Python oracle solution and builds an SBPS packet with exact BMW workspace
cardinalities: 11 BODY / 4 JOINT / 4 HINGE / 20 BAR.

The five-step runtime smoke requires five solver steps and five post-solve
steps, zero solver-vector join error, zero oracle error and BODY projection
applied=true while persistent vehicle state remains false.

A second SBPS packet is internally valid but changes one solved scalar. Native
runtime must reject it with `post-solve solved-vector join mismatch`.

## Boundary after Phase 610

Phase 610 proves the complete prepared provider-absent numerical chain
`reset → solve → post-solve BODY projection` on the native fixed-step
scheduler for an exact runtime-proven participant.

It still does not reconstruct authentic retail matrix/RHS assembly, runtime
reset selection, runtime constraint rows, provider-present dispatch, persistent
BODY integration or vehicle motion. Those remain evidence gates.
