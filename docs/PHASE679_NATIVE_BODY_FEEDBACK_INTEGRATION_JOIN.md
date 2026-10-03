# Phase 679 — native BODY feedback → integration anchor join

Phase 679 joins two already proven anchors inside the recovered half-step
boundary without claiming that the whole `FUN_00765470` function has been
ported.

The static schedule places post-solve BODY feedback before the BODY-array
persistent-state integrator:

```text
FUN_00765470
  -> ...
  -> FUN_007b3f40
  -> FUN_007b4110
  -> ...
  -> FUN_007b2270
       -> FUN_007bab70
```

The omitted calls remain omitted from the native claim.  Phase 679 freezes only
the relative order and byte handoff between the two proven state anchors.

No original game execution or new runtime capture is used.

## Native join

`shift_body_feedback_integration_join.hpp` adds:

```text
execute_proven_body_feedback_integration_join(...)
```

The implementation performs:

```text
raw BODY records
  -> Phase 678 execute_body_state_feedback_raw_step
       -> native generated constraints/reset/solve/post-solve feedback
       -> updated accumulator A/B bytes
  -> byte-exact raw handoff
  -> Phase 677 execute_fun_007b2270_body_buffer_with_basis_callback
       -> Phase 674 FUN_007bab70 arithmetic
       -> mandatory external FUN_007afdd0 provider per BODY
  -> persistent raw BODY records
```

The same raw byte buffer returned by the feedback stage is supplied directly to
the BODY-array integration stage.  There is no intermediate reconstruction of
unknown fields.

## Retail ordering preserved

The important ordering property is:

```text
post-solve accumulator feedback
BEFORE
persistent BODY origin/motion/prepared/cross/basis update
```

That order is static/source-backed.  Phase 679 does not move integration before
the solver and does not precompute all basis updates outside the BODY loop.

## Regression

The native regression reuses the established two-BODY/six-scalar all-reset
solver fixture so the solved vector is exactly zero.  This makes the storage
transition deterministic while still executing the complete Phase 678 feedback
chain.

Each raw BODY record also contains valid Phase 677 integration inputs.  With
`timestep = 0.25`, BODY 0 starts with:

```text
origin          = (1, 2, 3)
motion_triplet  = (4, 5, 6)
accumulator A   = (1, 2, 3)
accumulator B   = (4, 5, 6)
scalar +0x90    = 0.5
prepared_vector = (10, 20, 30)
cross_vector    = (0.1, 0, 0)
reciprocals     = (2, 3, 5)
basis           = identity
```

The external basis callback deliberately returns the input basis while recording
its rotation increment.  That is a regression provider, not an implementation
claim for `FUN_007afdd0`.

The check verifies:

- zero solved vector from the all-reset fixture;
- provider order/count for two BODY records;
- first rotation increment `0.025` and second `0.05`;
- BODY 0 origin becomes `(2, 3.25, 4.5)`;
- motion becomes `(4.5, 5.625, 6.75)`;
- prepared vector becomes `(10.25, 20.5, 30.75)`;
- cross vector becomes `(20.5, 61.5, 153.75)` through the existing tensor join;
- accumulator lanes handed off from feedback remain intact when the solved
  vector is zero;
- missing basis provider and non-finite timestep fail closed.

## Python oracle

`src/physics/body_feedback_integration_join_runtime.py` is intentionally a
scheduling oracle rather than another arithmetic implementation.  It verifies:

```text
FUN_007b4110 -> FUN_007b2270
```

and requires the exact bytes returned by the feedback callback to be the exact
input passed to the integration callback.

Coverage:

- `tests/test_body_feedback_integration_join_runtime.py`;
- `native_runtime/tests/body_feedback_integration_join_check.cpp`;
- CTest target `shift_runtime_body_feedback_integration_join`;
- `.github/workflows/native-physics-phase679.yml`.

## Explicit non-claims

Phase 679 does not claim:

- complete `FUN_00765470` behavior;
- implementation of calls omitted between the proven anchors;
- exact `FUN_007afdd0` float/x87 arithmetic;
- `FUN_00770e80` rendered-frame cadence;
- a complete retail fixed-step scheduler;
- vehicle/input ownership;
- scene or participant bootstrap.

It closes only the source-backed persistent-state anchor transition:

```text
post-solve BODY feedback
  -> persistent BODY integration
```
