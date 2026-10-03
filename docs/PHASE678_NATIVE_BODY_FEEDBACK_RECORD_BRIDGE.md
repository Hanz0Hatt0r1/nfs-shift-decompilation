# Phase 678 — native BODY feedback record bridge

Phase 678 connects the already ported solver/post-solve BODY feedback chain to
the source-backed raw `0x170` BODY storage introduced in Phase 677.

It is deliberately narrower than `FUN_00765470`: this phase does not schedule the
persistent pose integrator, relation refresh, wheel update, or rendered-frame
loop.  It only joins the proven accumulator storage lanes to the existing native
`execute_body_state_feedback_step()` chain and writes its post-solve accumulator
result back to the same raw records.

No original game execution or new runtime capture is used.

## Proven storage boundary

The BODY ABI fixes the six persistent accumulator doubles as:

```text
accumulator A  +0x48/+0x50/+0x58
accumulator B  +0x60/+0x68/+0x70
```

The BODY record stride is `0x170` bytes.  Phase 678 therefore exposes exactly 48
writer bytes per record and preserves every byte outside `+0x48..+0x77`.

The raw bridge does not decode or validate unrelated origin/basis/tensor fields,
because the solver feedback step does not consume them through this API.

## Native chain

`shift_body_feedback_record_bridge.hpp` adds:

```text
decode_body_accumulators_from_buffer(...)
apply_body_accumulators_to_buffer(...)
execute_body_state_feedback_raw_step(...)
```

The joined path is:

```text
raw BODY accumulator A/B lanes
  -> BodyAccumulatorState[]
  -> execute_body_state_feedback_step
       -> generated constraint refresh
       -> solver matrix/RHS generation
       -> relation-derived reset selection
       -> builtin sparse solve
       -> post-solve BODY projection
  -> BodyAccumulatorState[]
  -> raw BODY accumulator A/B lanes
```

This reuses the already tested solver/post-solve implementation rather than
introducing another arithmetic copy.

## Fail-closed behavior

The bridge rejects:

- `body_count * 0x170` overflow;
- raw byte-size/body-count mismatch;
- NaN/Inf in any input accumulator lane;
- NaN/Inf in any output accumulator lane;
- all existing solver topology, relation, matrix-anchor, and cardinality errors
  propagated by `execute_body_state_feedback_step()`.

No unknown BODY field is synthesized or overwritten.

## Reference oracle and regression

`src/physics/body_feedback_record_bridge_runtime.py` independently freezes the
raw storage contract:

- record size `0x170`;
- exact accumulator offsets;
- exact little-endian f64 decoding/writing;
- exact 48-byte writer mask;
- preservation of every unrelated byte;
- size/count and non-finite rejection.

Coverage:

- `tests/test_body_feedback_record_bridge_runtime.py`;
- `native_runtime/tests/body_feedback_record_bridge_check.cpp`;
- CTest target `shift_runtime_body_feedback_record_bridge`;
- `.github/workflows/native-physics-phase678.yml`.

The native regression uses the established two-BODY/six-scalar solver fixture.
It changes accumulator inputs in the raw records, passes them through the real
native feedback step, and uses the all-reset fixture so the solved vector is
exactly zero.  The resulting accumulators therefore remain equal to the raw
input state while the regression still executes the complete generated
constraint/reset/solve/post-solve chain.

## Scope boundary

Phase 678 proves this native storage transition:

```text
source-backed raw BODY accumulators
  -> native solver/post-solve feedback
  -> source-backed raw BODY accumulators
```

It does **not** prove or schedule:

- `FUN_007b2270` / `FUN_007bab70` pose integration after feedback;
- exact `FUN_007afdd0` basis rotation arithmetic;
- all work inside `FUN_00765470`;
- `FUN_00770e80` rendered-frame cadence;
- input/controller ownership;
- vehicle object ownership or scene bootstrap.

Those remain separate evidence-gated integration boundaries.
