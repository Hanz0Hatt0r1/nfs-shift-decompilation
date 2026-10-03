# Phase 686 — typed `FUN_00763570` precomputed-transform → feedback join

Phase 685 inserted the statically proven `FUN_00763570` anchor before the existing
native solver/post-solve/persistent BODY path, but deliberately represented that
anchor as an opaque callback.

Phase 686 narrows that callback using the already-native Phase 668 contract.  The
remaining transform production stays external, while the source-backed
four-wheel `FUN_00763570` batch now executes in native code before entering the
Phase 685 half-step continuation.

## Composed path

```text
precomputed transform provider
  -> Phase 668 execute_fun_00763570_precomputed_batch
       -> four FUN_00755f80 handoffs in wheel order 0,1,2,3
       -> source-backed rear-pair averaging gate
  -> Phase 685 FUN_00765470 join
       -> FUN_007b3f40 solver/reset path
       -> FUN_007b4110 post-solve BODY feedback
       -> FUN_007b2270 persistent BODY integration
```

The provider supplies only values that Phase 668 already keeps outside the native
boundary: the local vector produced before longitudinal-component extraction and
the reconstructed vector produced after the unresolved transform.

## Native contract

Files:

```text
native_runtime/include/shift_fun_00763570_precomputed_feedback_join.hpp
native_runtime/src/fun_00763570_precomputed_feedback_join.cpp
```

Format:

```text
SHIFT.NativeFun00763570PrecomputedFeedbackJoin/1
```

`Fun00763570PrecomputedInput` contains exactly four `WheelLongitudinalInput`
records plus the already-proven three rear-pair gate inputs.  The wrapper requires
a provider, invokes it exactly once inside the Phase 685 `FUN_00763570` anchor,
and executes:

```text
execute_fun_00763570_precomputed_batch(...)
```

before the Phase 685 feedback/integration continuation is allowed to run.

This means the previous `void()` anchor no longer hides the arithmetic already
admitted by Phase 668.

## Reference oracle

Scheduling-only oracle:

```text
src/physics/fun_00763570_precomputed_feedback_join_runtime.py
```

Regression:

```text
tests/test_fun_00763570_precomputed_feedback_join_runtime.py
```

The oracle freezes only the composition order:

```text
provider -> native/precomputed batch -> Phase 685 continuation
```

It does not duplicate either the wheel arithmetic or solver arithmetic.

## Native regression

`shift_runtime_fun_00763570_precomputed_feedback_join_check` reuses the Phase 685
two-BODY / six-scalar deterministic fixture and adds a four-wheel Phase 668
fixture.

It verifies:

- provider invocation exactly once;
- wheel indices remain `0,1,2,3`;
- source-order reconstructed-vector subtraction;
- longitudinal components `1,2,3,4` before the rear gate;
- rear-pair gate produces `3.5,3.5` in slots 2 and 3;
- Phase 685 solver result and reset metadata remain unchanged;
- persistent BODY integration still receives the same rotation increments;
- BODY 0 preserves the established persistent result:
  - origin `(2.0, 3.25, 4.5)`;
  - motion `(4.5, 5.625, 6.75)`;
  - prepared vector `(10.25, 20.5, 30.75)`;
  - cross vector `(20.5, 61.5, 153.75)`;
- missing provider, malformed wheel identity, and non-finite active transform
  payload fail closed.

## Evidence boundary

Phase 686 still does **not** implement or infer `FUN_007af010`.  The provider is
therefore not optional production glue; it is the explicit unresolved transform
boundary inherited from Phase 668.

The phase also does not claim:

- complete `FUN_00755f80` transform production;
- complete `FUN_00763570` semantics outside the admitted Phase 668 batch;
- adjacency of the four Process 1 anchors inside `FUN_00765470`;
- complete `FUN_00765470` semantics;
- exact repeated two-half-step refresh of every external state producer;
- rendered-frame cadence or input/control ownership;
- closure of the Phase 680 `FUN_007afdd0` machine scalar-production gate.

The machine-readable/native report therefore keeps:

```text
fun_007af010_implemented = false
complete_fun_00763570_semantics = false
complete_fun_00765470_semantics = false
```

## Next gate

The remaining `FUN_00763570` blocker is now specifically the transform producer,
not the four-wheel batch arithmetic.  The next safe reduction requires exact
source/machine evidence for `FUN_007af010` (and any required paired transform
state), or a stronger precomputed producer contract.  Until then, the typed
provider remains mandatory.
