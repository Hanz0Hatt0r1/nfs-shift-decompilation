# Phase 676 — native FUN_00766510 orchestration with explicit primary-application barrier

Phase 676 composes two already-proven portions of the `FUN_00766510` contact
response path without inventing the still-unresolved primary response-vector
application.

The source-backed order available at this boundary is:

```text
FUN_00765c40 query result
  -> +0x38e0 query scalar
  -> FUN_00766510 clamp/directional/FUN_007551e0 response stage
  -> [primary response transform/application: exact contract unresolved]
  -> FUN_00758fc0(this + 0x37d8)
  -> FUN_00758fc0(this + 0x3858)
```

Phase 667 already implements the query/response join.  Phases 659 and 664 already
implement one auxiliary record and the exact two-record accumulator handoff.
Phase 676 connects those proven islands through an explicit evidence barrier.

## Evidence barrier

`ContactResponseOrchestrationInput` requires
`body_accumulator_after_primary_application` as an `std::optional` value.

This state is **not** derived from the generated `FUN_007551e0` response vector.
The exact caller-side transform/application into `FUN_007baa70` is still not
frozen by the static contract.  Therefore:

- absent post-primary state is rejected;
- NaN or infinity in that state is rejected;
- a zero accumulator is never synthesized as a fallback;
- the primary response vector is never silently discarded and replaced by a
  guessed application;
- the auxiliary pair starts only from the explicitly supplied post-primary
  accumulator.

This makes the unresolved producer visible in the native type rather than hiding
it behind a placeholder constant.

## Shared BODY domain

The auxiliary pair reuses `query_response.body_frame`, which is the same BODY
frame already consumed by the Phase 663 response-input transform.  The Phase 676
input intentionally does not expose a second auxiliary frame.  This prevents a
caller from joining the two halves using inconsistent BODY domains.

The point-transform state used by `FUN_00758fc0` remains an explicit input because
its source fields are independently proven by Phase 658.

## Reference oracle

`src/physics/contact_response_orchestration_runtime.py` mirrors the new
orchestration rule using existing Python references for:

- the `FUN_00766510` contact-response arithmetic;
- the `FUN_00758fc0` local-response arithmetic;
- the `FUN_007baa70` six-channel BODY accumulator delta.

Its deterministic fixture freezes:

- hit query scalar `10 - 7 = 3`;
- response gain `7`;
- response vector `(1, 20, 54)`;
- auxiliary response `(1, -4, -9)`;
- explicit post-primary accumulator
  `angular=(1,2,3), linear=(4,5,6)`;
- two auxiliary applications in offsets `+0x37d8`, then `+0x3858`;
- final accumulator
  `angular=(193,-318,323), linear=(4,69,70)`.

The non-zero seed is deliberate: it proves that the phase preserves the external
primary-application state and adds the two auxiliary contributions instead of
starting from a guessed zero state.

## Native regression and CI

`shift_runtime_contact_response_orchestration_check` mirrors the same fixture and
also compares the final accumulator to a direct call of the already-proven
`execute_fun_00766510_aux_contact_pair()` starting from the supplied barrier
state.  It tests missing and non-finite barrier rejection.

The incremental physics CMake registration and `native-physics-recent` workflow
build, execute and verify the new target and Python oracle.

## Explicit non-claims

Phase 676 does **not** claim:

- the exact primary `FUN_007551e0` response transform/application;
- that the supplied post-primary accumulator can yet be produced by the native
  runtime scheduler;
- a full port of `FUN_00766510`;
- collision-provider ownership;
- `FUN_00770e80` frame scheduling;
- persistent BODY origin/basis/motion evolution.

The next transition through this barrier must wait for Process 1 to freeze the
primary application transform or another source-backed producer of the exact
post-primary BODY accumulator state.
