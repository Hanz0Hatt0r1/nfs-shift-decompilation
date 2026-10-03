# Phase 653 — runtime BODY feedback scheduler

Phase 652 closed one provider-absent dynamic physics step as an isolated
primitive. Phase 653 places that primitive on the native fixed-step path so the
next solver step consumes the previous step's persistent BODY accumulator
state instead of replaying the original prepared SBFR RHS/solution.

The scheduler contract is:

```text
SHIFT.NativeBodyFeedbackScheduler/1
```

implemented by `native_runtime/src/runtime_body_feedback_scheduler.hpp` and
owned by `NativeRuntimeState`.

## Fixed-step order

When explicitly enabled, every `NativeRuntimeState::fixed_step()` now executes:

```text
validate physics workspace + proven participant identity
  -> camera guarded update begin
  -> native input/physics tick bookkeeping
  -> previous persistent BODY accumulator state
  -> Phase 652 execute_body_state_feedback_step()
     -> GBCF BODY preprojection feedback
     -> CSRF FUN_007b3ed0 refresh
     -> FUN_007bc680 / FUN_007ba570 matrix+RHS generation
     -> CRRF FUN_007b3f40 reset selection
     -> FUN_007b2210 diagonal reset
     -> FUN_007b0f20 sparse solve
     -> FUN_007b4110 post-solve row application
  -> retain resulting BODY accumulator state for the next fixed step
  -> camera guarded update completion
```

The scheduler is disabled by default. Therefore the existing low-level CLI
solver modes remain available for individual packet/oracle regression and are
not silently changed.

## Vertical-slice launch transport

`tools/run_native_vertical_slice.py` now activates the scheduler through a
dedicated environment contract:

```text
SHIFT_NATIVE_BODY_FEEDBACK=1
SHIFT_NATIVE_BODY_FEEDBACK_SOLVER_FRAME=<SBFR>
SHIFT_NATIVE_BODY_FEEDBACK_GBCF=<GBCF>
SHIFT_NATIVE_BODY_FEEDBACK_CSRF=<CSRF>
SHIFT_NATIVE_BODY_FEEDBACK_CRRF=<CRRF>
SHIFT_NATIVE_BODY_FEEDBACK_SBPS=<SBPS>
```

The vertical-slice runner deliberately stops passing the legacy
`--solver-frame`, `--generated-body-constraint-frame`,
`--constraint-sample-relation-frame`, `--constraint-relation-reset-frame`,
`--post-solve-projection` and `--persist-post-solve-body-state` options. This
prevents the old static replay loop and the new dynamic feedback scheduler from
executing the same physics chain in parallel.

The profile format itself is unchanged. All five packets are still validated
before launch and `persist_post_solve_body_state=true` remains mandatory.

## Fail-closed runtime boundary

Before executing a scheduled step, native state requires:

- a ready physics workspace;
- a ready participant instance;
- a proven registry/selector identity join;
- scheduler BODY count equal to workspace BODY count;
- scheduler scalar count equal to workspace scalar count.

Phase 652 continues to enforce row identity, dynamic reset selection, finite
values and the static matrix/topology anchor. Any violation aborts the runtime
step instead of dropping back to replay behavior.

## Regression coverage

`shift_runtime_body_feedback_scheduler_check` constructs the same six-scalar
JOINT/HINGE/BAR synthetic domain used by the Phase 652 feedback regression,
configures a complete `NativeRuntimeState`, and executes two consecutive fixed
steps.

It requires:

- two scheduler executions for two runtime fixed steps;
- input bookkeeping to remain active while feedback executes;
- six dynamically selected reset nodes;
- zero matrix-anchor drift;
- matching BODY/scalar workspace cardinality;
- explicit rejection of a mismatched runtime BODY workspace.

The Python vertical-slice tests also require the scheduler environment to be
injected into the child process and require all legacy replay CLI solver flags
to be absent from the launch plan.

## Remaining boundary

The internal provider-absent constraint-solver state loop is now scheduled
across consecutive native fixed steps.

This still does **not** prove or implement the persistent vehicle motion bridge:
BODY position/orientation and any engine-level velocity/motion transform update
remain separate evidence-gated work. Input intent is still only admitted to the
native tick boundary; retail drivetrain/wheel control propagation is not
claimed here. Provider-present dispatch and the retail game loop also remain
outside scope.
