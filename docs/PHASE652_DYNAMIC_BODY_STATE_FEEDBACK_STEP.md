# Phase 652 — dynamic BODY state feedback solver step

Phase 651 proved that the six persistent `FUN_007b4110` BODY accumulator
channels are the same storage consumed by the next `FUN_007bc680` preprojection
and that GBCF/CSRF/SBPS rows share exact BODY/scalar identity. Phase 652 turns
that proven seam into one executable provider-absent solver step.

The new primitive is:

```text
SHIFT.NativeBodyStateFeedbackStep/1
```

implemented by `execute_body_state_feedback_step()` in the existing
`shift_runtime_physics` library.

## Exact step order

For one supplied persistent BODY state, the function executes:

```text
persistent BODY +0x48/+0x50/+0x58 and +0x60/+0x68/+0x70
  -> copy into GBCF preprojection input
  -> CSRF FUN_007b3ed0 relation refresh
  -> FUN_007bc680 BODY contribution generation
  -> FUN_007ba570 global matrix/RHS export
  -> CRRF FUN_007b3f40 reset-node selection
  -> FUN_007b2210 diagonal reset
  -> FUN_007b0f20 sparse solve
  -> FUN_007b4110 JOINT/HINGE/BAR row application
  -> next persistent BODY accumulator state
```

No prepared RHS or prepared solved vector is reused after BODY feedback is
applied.

## Solver topology anchor

The sparse forward/reverse record graph is still taken from the admitted SBFR
because that graph has already been recovered and proof-gated. Reusing it is
allowed only while the generated matrix remains exactly anchored to the
admitted SBFR matrix within the explicit numerical tolerance.

This is an important fail-closed distinction:

- the **RHS is expected to change** when persistent BODY accumulator state
  changes;
- the **matrix is not allowed to change** in this phase, because BODY frame,
  position, tensor, relation geometry and row layout remain static;
- if generated matrix coefficients move, execution stops rather than assuming
  the old sparse topology still applies.

The dynamic reset set comes directly from CRRF relation bit0 state and is
normalized before `FUN_007b2210`; the step does not force it back to the
original SBFR reset list. This keeps the primitive ready for later authentic
relation-state mutation scheduling.

## Post-solve behavior

The solved vector is passed to the Phase 651 arbitrary-vector
`apply_post_solve_body_projection_rows()` kernel. Therefore a regenerated RHS
can produce a different solved vector and still execute the exact recovered
`FUN_007b4110` JOINT/HINGE/BAR algebra.

The older SBPS oracle functions remain unchanged and continue to validate the
original captured/prepared one-step vector. They are still useful as the
admission anchor for the initial frame.

## Regression

The existing `shift_runtime_body_state_feedback_check` now additionally builds a
six-scalar synthetic topology from the generated source matrix and selects all
six reset lanes through one JOINT, one HINGE and one BAR CRRF relation.

It verifies that:

- feedback regenerates matrix/RHS through the native source-backed path;
- CRRF selects exactly six reset calls/nodes;
- all-reset solve produces the expected zero vector;
- changed BODY accumulator state leaves the matrix anchor unchanged;
- a tampered solver-topology matrix is rejected before solve/post-solve.

## Remaining boundary

Phase 652 is still a standalone physics primitive. The next integration step is
to place it behind an explicit `shift_runtime` scheduler mode so consecutive
fixed steps use the previous step's BODY accumulator result instead of replaying
the static SBFR RHS.

This still does **not** assign persistent vehicle position, orientation or
velocity semantics. Those remain a separate boundary after the internal solver
state loop is closed in the scheduler.
