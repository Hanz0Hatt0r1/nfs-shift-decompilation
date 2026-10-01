# Phase 608 — prepared builtin solver frame on the native fixed-step scheduler

Phase 606 adds a fail-closed prepared provider-absent solver frame and proves
native parity for the exact recovered builtin sequence:

`FUN_007b2210 → FUN_007b0f20`.

Phase 607 can promote one concrete participant into native state from exact
runtime identity evidence without collapsing the manager-registry index and
selector ordinal domains.

Phase 608 joins those two already-proven boundaries on the native fixed-step
scheduler.

## Runtime option

`native_runtime/shift_runtime` adds:

```text
--solver-frame FILE
```

The file is the Phase 606 `SHIFT.NativeBuiltinSolverFramePacket/1` (`SBFR`)
packet.

The option is optional. Without it, the native physics scheduler behaves as it
did before Phase 608.

## Admission gates

A solver frame is admitted only when all of these conditions are true:

1. `--physics-manifest` is supplied and resolves to a ready native physics
   workspace;
2. `--participant-boundary` is supplied;
3. the participant contract has already been promoted by Phase 607 so
   `participant_ready=true`;
4. the participant pointer identity join is proven;
5. the SBFR packet passes the Phase 606 native loader, including all four proof
   bits:
   - provider absent;
   - matrix/RHS ready;
   - reset-node selection ready;
   - sparse graph ready;
6. the solver-frame scalar count exactly equals the native workspace scalar
   count.

Any failed gate aborts before fixed-step solver execution.

## Fixed-step execution

For every native fixed step:

1. the existing camera/input/participant state boundary advances;
2. when `--solver-frame` is active, participant readiness is rechecked;
3. the exact prepared frame executes:
   `FUN_007b2210 → FUN_007b0f20`;
4. native output is checked against the Phase 606 Python oracle;
5. the scheduler records execution telemetry.

The same prepared frame may be replayed across deterministic regression steps.
That replay is test/control infrastructure and is not claimed to be retail BMW
matrix assembly.

## Telemetry

`SHIFT.NativeRuntimeFrameLoop/1` adds:

- `physics_solver_frame_loaded`;
- `physics_solver_frame_scalar_count`;
- `physics_solver_frame_reset_node_count`;
- `physics_solver_frame_steps`;
- `physics_solver_frame_max_oracle_error`;
- `physics_solver_provider_present=false`;
- `physics_solver_post_solve_body_state_applied=false`.

The final two fields make the remaining boundary explicit: Phase 608 runs only
the provider-absent builtin numerical branch and does not apply the solved
vector through `FUN_007b4110`.

## Linux CI

The structural three-frame scene smoke does not supply a solver frame and
requires:

- `physics_solver_frame_loaded=false`;
- `physics_solver_frame_steps=0`.

The deterministic five-step smoke first builds a synthetic 40-scalar frame,
matching the admitted BMW SDF workspace size. It uses:

- Phase 607 participant-ready runtime evidence;
- provider-absent proof;
- explicit matrix/RHS;
- explicit reset node;
- exact dense regression sparse graph.

The runtime then requires:

- workspace scalars = 40;
- solver-frame scalars = 40;
- solver steps = 5;
- reset-node count = 1;
- maximum native/Python oracle error = 0;
- provider path not used;
- post-solve body-state application not performed.

The 40-scalar frame is explicitly a synthetic regression fixture. It is not
retail matrix/RHS evidence.

## Boundary after Phase 608

The native scheduler can now execute an exact, evidence-prepared builtin solver
frame for an exact, runtime-proven participant.

Still unresolved:

- retail per-step matrix/RHS assembly;
- authentic runtime reset-node selection;
- provider-present dispatch;
- specialized-provider numerical parity;
- mapping the solved scalar vector into BODY/JOINT/HINGE/BAR state through
  `FUN_007b4110`;
- force integration and vehicle motion.

The next safe numerical step is to reconstruct/transport the post-solve
`FUN_007b4110` body-state projection independently of the still-capture-gated
matrix assembly/provider path.
