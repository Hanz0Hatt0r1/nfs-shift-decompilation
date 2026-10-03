# Phase 651 — BODY state feedback contract

Phase 611 preserved the six `FUN_007b4110` BODY accumulator channels between
native fixed steps, but the generated next-step `FUN_007bc680` input still came
from the original prepared GBCF. Phase 651 closes the structural identity gate
required before those persistent channels can be fed back into the next solver
assembly.

No new physical labels are assigned. The fields remain the exact BODY storage
channels already recovered from the retail source:

- angular group: `+0x48/+0x50/+0x58`;
- linear group: `+0x60/+0x68/+0x70`.

Those are also the fields consumed by the `FUN_007bc680` preprojection path.

## `SHIFT.NativeBodyStateFeedbackContract/1`

`verify_body_state_feedback_contract()` joins three existing evidence domains:

1. GBCF BODY preprojection state;
2. CSRF ownership plus the source-backed `FUN_007b3ed0` refreshed constraint
   rows;
3. SBPS `FUN_007b4110` BODY/JOINT/HINGE/BAR rows.

Admission requires:

- exact BODY cardinality across GBCF, CSRF and SBPS;
- initial SBPS BODY angular/linear state equal to the corresponding GBCF
  preprojection state;
- exact source-order JOINT/HINGE/BAR relation cardinality;
- exact positive/negative BODY identity for every post-solve row;
- exact scalar-base identity at both relation endpoints and the SBPS row;
- JOINT post-solve lever arms equal the refreshed endpoint positions;
- HINGE post-solve angular/linear rows equal the refreshed endpoint rows;
- BAR post-solve lever arms equal the refreshed endpoint points and the SBPS
  direction equal both refreshed endpoint directions.

A mismatch in any field blocks feedback instead of silently joining unrelated
prepared artifacts.

## Feedback operation

`apply_body_accumulator_feedback()` copies a prepared GBCF and replaces only:

```text
BODY +0x48/+0x50/+0x58
BODY +0x60/+0x68/+0x70
```

with the supplied persistent accumulator state. Position, frame, correction,
axis, inverse scalar, tensor, row layout and constraint samples are unchanged.
The ordinary CSRF refresh can then run on that copied frame.

## Arbitrary solved-vector row kernel

Phase 651 also exposes `apply_post_solve_body_projection_rows()`. It executes the
already ported `FUN_007b4110` JOINT/HINGE/BAR row algebra for any finite solved
vector with the same scalar cardinality, without requiring that vector to equal
the one-step SBPS oracle.

This does not weaken the existing SBPS verifier. The previous
`execute_post_solve_body_projection_*()` functions continue to enforce the
prepared solved-vector and one-step oracle. The new row kernel is a lower-level
primitive intended for the next phase, where the next-step RHS is regenerated
from feedback state and therefore can legitimately produce a different solved
vector.

## Native regression

`shift_runtime_body_state_feedback_check` verifies:

- a zero-error GBCF/CSRF/SBPS seed and row join;
- exact replacement of only the next-step angular/linear preprojection state;
- arbitrary solved-vector execution through the source-backed post-solve row
  algebra;
- rejection of a mismatched post-solve JOINT row.

## Remaining boundary

Phase 651 proves that the persistent BODY accumulator output and next-step
preprojection input are the same retail storage channels and that the prepared
post-solve rows belong to the same refreshed relation set.

It does **not** yet schedule that feedback in `shift_runtime`. The next phase can
safely compose:

```text
persistent BODY accumulators
  -> GBCF preprojection state
  -> CSRF refresh
  -> FUN_007bc680/FUN_007ba570 generated matrix + RHS
  -> CRRF reset selection
  -> FUN_007b2210/FUN_007b0f20
  -> FUN_007b4110
  -> next persistent BODY accumulators
```

Persistent vehicle position/orientation/velocity integration remains a separate
unresolved boundary after that solver-state loop is closed.
