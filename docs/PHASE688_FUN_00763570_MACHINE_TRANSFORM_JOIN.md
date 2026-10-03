# Phase 688 — `FUN_00763570` machine-transform → feedback/integration join

Phase 688 removes the last **precomputed reconstructed-vector** boundary from the
Phase 686 `FUN_00763570` native join.

Phase 687 established machine-backed implementations for the two transform helpers
used by `FUN_00755f80`:

```text
FUN_007af0a0(matrix<float32>, vector<float64>)
FUN_007af010(matrix<float32>, scalar<float64>)
```

The retail instruction slices prove QWORD vector/scalar operands, float32 matrix
coefficients and x87 multiply/add ordering.  The native helpers preserve that
shape with `long double` intermediates and final float64 stores.

Phase 688 composes those helpers into the already admitted chain:

```text
FUN_00765470
  -> FUN_00763570
       -> wheel 0..3
            -> FUN_007af0a0(body_frame, shared_velocity)
            -> local.x
            -> FUN_007af010(body_frame, local.x)
            -> shared_velocity -= reconstructed_vector
       -> proven rear-pair averaging gate
  -> existing Phase 685 solver/post-solve/persistent BODY continuation
```

This is still not a complete `FUN_00763570` or `FUN_00765470` implementation.
Only the previously external transform results are now produced natively.

## Native contract

New files:

```text
native_runtime/include/shift_fun_00763570_machine_feedback_join.hpp
native_runtime/src/fun_00763570_machine_feedback_join.cpp
```

Format:

```text
SHIFT.NativeFun00763570MachineFeedbackJoin/1
```

`WheelLongitudinalMachineInput` carries only the machine-source inputs that are
needed for the recovered transform path:

- exact wheel index;
- 3x3 float32 BODY frame;
- float64 shared velocity triplet.

`Fun00763570MachineInput` keeps the Phase 668 caller gates:

- exactly four wheels;
- rear-pair-average enable;
- mode;
- global configuration byte.

The provider no longer supplies either `local_velocity` or
`reconstructed_world_velocity`.

## Transform composition

`build_fun_00763570_machine_precomputed_input()` performs, in retail wheel order:

```text
local = transform_fun_007af0a0_refresh(body_frame, shared_velocity)
reconstructed = transform_fun_007af010_refresh(body_frame, local[0])
```

It then constructs the already-proven Phase 668/686 precomputed contract and
reuses:

```text
execute_fun_00765470_precomputed_longitudinal_feedback_join(...)
```

This deliberately keeps one implementation of the four-wheel subtraction,
rear-pair averaging, solver, post-solve feedback and persistent BODY integration
instead of duplicating those kernels.

## Reference oracle

Python reference/orchestration layer:

```text
src/physics/fun_00763570_machine_feedback_join_runtime.py
```

Regression:

```text
tests/test_fun_00763570_machine_feedback_join_runtime.py
```

The oracle consumes the canonical Phase 687
`SHIFT.MatrixVectorTransformRuntime/3` helpers and freezes:

```text
provider
-> FUN_007af0a0/FUN_007af010 machine transforms
-> Phase 686 continuation
```

It rejects malformed wheel cardinality/order and non-finite consumed transform
values.

## Native regression

`shift_runtime_fun_00763570_machine_feedback_join_check` uses a deterministic
four-wheel diagonal-frame fixture.  For wheel 0:

```text
frame = diag(2, 3, 4)
shared = (10, 20, 30)
local = (20, 60, 120)
reconstructed = (40, 0, 0)
shared_after = (-30, 20, 30)
```

The four source-visible longitudinal components are `20,22,24,26`; with the
already-proven rear average gate enabled, reported components 2 and 3 both become
`25`.

The same regression continues through the Phase 685/679 native chain and verifies
that persistent BODY origin still reaches the established deterministic result.
It also checks fail-closed behavior for:

- missing machine input provider;
- malformed wheel order/index;
- non-finite shared velocity.

## Precision boundary

Phase 687 proves helper bytes, operand widths and instruction operation order.
Phase 688 therefore no longer treats `FUN_007af010` as an unresolved transform
producer.

One precision boundary remains explicit: the ambient x87 control word at every
retail callsite has not been proven.  Native `long double` intermediates model the
x87-shaped arithmetic but are not promoted to universal bit-for-bit retail parity
until that control-state boundary is closed.

Therefore Phase 688 reports:

```text
fun_007af0a0_machine_helper_used = true
fun_007af010_machine_helper_used = true
precomputed_reconstructed_vector_provider_removed = true
ambient_x87_control_word_proven = false
complete_fun_00763570_semantics = false
complete_fun_00765470_semantics = false
```

## Non-goals

Phase 688 does **not**:

- infer physical axis names or units;
- claim all local work inside `FUN_00763570` is implemented;
- claim adjacency between Process 1 schedule anchors;
- close the independent `FUN_007afdd0` scalar-production/x87 control-state gate;
- prove rendered-frame cadence;
- prove input/control ownership;
- create or admit a vehicle participant;
- run `SHIFT.exe` or request new runtime capture.
