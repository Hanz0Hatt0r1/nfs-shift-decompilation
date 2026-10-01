# Phase 609 — prepared native FUN_007b4110 post-solve projection

Phase 608 executes an evidence-prepared provider-absent builtin solver frame on
the native fixed-step scheduler, but deliberately stops before applying the
solved scalar vector back into BODY state.

Phase 609 closes that numerical boundary independently of matrix/RHS assembly,
reset selection and provider dispatch.

## Source-backed contract

`FUN_007b4110` consumes the solved vector at PhysicsSystem `+0x40` in the
recovered order JOINT → HINGE → BAR.

- JOINT consumes three scalars and applies the same vec3 through
  `FUN_007baa70` / `FUN_007baaf0`; linear receives ±contribution and angular
  receives ±(lever_arm × contribution).
- HINGE consumes two scalars and updates only angular channels with
  `solved[0] * angular_row + solved[1] * linear_row` on the positive BODY and
  the exact subtraction on the negative BODY.
- BAR consumes one scalar, scales the sampled direction, then uses the same
  positive/negative BODY accumulator helpers as JOINT.

No physical unit labels are assigned to the six BODY accumulator channels.

## Prepared contract

New builder: `src/physics/native_post_solve_body_projection.py`.

Input: `SHIFT.NativePostSolveBodyProjectionInput/1`.

Output: `SHIFT.NativePostSolveBodyProjection/1`.

Binary packet: `SHIFT.NativePostSolveBodyProjectionPacket/1` (`SBPS`).

The input must explicitly prove `solved_vector_ready`, `body_state_ready` and
`constraint_rows_ready`, and must provide initial BODY states, the complete
solved vector and explicit JOINT/HINGE/BAR rows. None of those runtime-only
values are derived from static assets.

SBPS stores the proof mask, body/scalar/constraint counts, initial BODY state,
solved vector, constraint rows and Python-oracle final BODY state. JOINT/HINGE/
BAR scalar widths remain exactly 3/2/1.

## Native implementation

Native declarations live in `native_runtime/include/shift_post_solve_projection.hpp`
with execution in `native_runtime/src/post_solve_projection.cpp`.

The native executor ports the recovered accumulator cross product, JOINT
positive/negative application, direct HINGE angular update, BAR direction
scaling and JOINT → HINGE → BAR ordering, then compares every final BODY
channel against the Python oracle.

Standalone verifier:

```bash
native_runtime/build/shift_runtime_post_solve_projection_check \
  out/native-post-solve/post_solve.sbps
```

Prepare a packet with:

```bash
python shift_importer.py native-post-solve-projection \
  post-solve-input.json \
  out/native-post-solve
```

## CI

Linux CI prepares one synthetic fixture containing JOINT, HINGE and BAR, runs
the native verifier and requires `FUN_007b4110`, body count 3, oracle parity,
`fixed_step_runtime_integration=false` and status `ok`. Clearing one proof bit
must be rejected by the native loader.

## Boundary after Phase 609

Phase 609 proves native parity for post-solve BODY projection itself. It does
not yet join a Phase 608 solver result to this packet on the fixed-step
scheduler, and it does not derive retail matrix/RHS assembly, runtime reset
selection, provider-present dispatch, runtime constraint rows, force
integration or vehicle motion.

The next safe step is to join the Phase 608 solved vector to a separately
prepared Phase 609 projection only when scalar cardinality, participant
identity and explicit BODY/constraint evidence all agree.
