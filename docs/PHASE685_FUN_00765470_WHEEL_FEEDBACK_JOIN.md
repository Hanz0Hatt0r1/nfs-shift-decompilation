# Phase 685 — `FUN_00765470` wheel-shared-triplet → feedback/integration join

Process 1 `SHIFT.GhidraBodyUpdateScheduleFrontier/2` proves the required relative
anchor order inside the recovered half-step bridge `FUN_00765470`:

```text
FUN_00763570
FUN_007b3f40
FUN_007b4110
FUN_007b2270
```

The frontier proves order, not adjacency. Other local work and direct/indirect
calls may occur between these anchors.

Phase 679 already executes the admitted native chain covering generated
constraint work, `FUN_007b3f40` solver/reset flow, `FUN_007b4110` post-solve BODY
feedback, and the later `FUN_007b2270 -> FUN_007bab70` persistent BODY update.
Phase 685 therefore does not duplicate that arithmetic. It adds only the proven
preceding `FUN_00763570` boundary and then delegates to the existing Phase 679
join.

## Native contract

New files:

```text
native_runtime/include/shift_fun_00765470_wheel_feedback_join.hpp
native_runtime/src/fun_00765470_wheel_feedback_join.cpp
```

Format:

```text
SHIFT.NativeFun00765470WheelFeedbackJoin/1
```

The new entry point is:

```text
execute_fun_00765470_wheel_feedback_join(...)
```

It requires a `Fun00763570WheelSharedTripletCallback`, invokes it exactly once,
and only then calls:

```text
execute_proven_body_feedback_integration_join(...)
```

from Phase 679.

This preserves one implementation of the solver/post-solve/persistent BODY path
instead of introducing a second arithmetic copy.

## Reference oracle

Python scheduling oracle:

```text
src/physics/fun_00765470_wheel_feedback_join_runtime.py
```

Regression:

```text
tests/test_fun_00765470_wheel_feedback_join_runtime.py
```

The oracle verifies that the `FUN_00763570` callback occurs before entry into the
Phase 679 callback and that the exact input bytes are handed to that callback
without reconstruction. It deliberately does not reproduce solver arithmetic.

## Native regression

`shift_runtime_fun_00765470_wheel_feedback_join_check` reuses the established
Phase 679 two-BODY / six-scalar all-reset fixture.

The native wrapper executes:

```text
FUN_00763570 callback
  -> Phase 679 native feedback/integration join
       -> generated constraint refresh/export
       -> relation-derived reset selection / builtin solve
       -> post-solve BODY feedback
       -> raw BODY byte handoff
       -> persistent BODY integration
```

The all-reset solver result is exactly zero, so this remains deterministic while
still traversing the admitted native solver/post-solve chain.

At fixture `timestep=0.25`, BODY 0 must retain the existing Phase 679 expected
persistent result:

```text
origin          = (2.0, 3.25, 4.5)
motion_triplet  = (4.5, 5.625, 6.75)
prepared_vector = (10.25, 20.5, 30.75)
cross_vector    = (20.5, 61.5, 153.75)
```

The basis provider additionally fails the test if persistent integration is
reached before the `FUN_00763570` anchor callback. Missing `FUN_00763570` and
non-finite timestep inputs fail closed.

The `0.25` value is a deterministic regression input. Phase 685 does not promote
that fixture value to a newly proven retail timestep semantic.

## Evidence boundary

Phase 685 proves only this additional integration fact:

```text
FUN_00763570
  BEFORE
existing Phase 679 solver/post-solve/persistent BODY chain
```

Together with the existing static frontier, the native admitted anchors are now
ordered consistently with:

```text
FUN_00765470
  -> FUN_00763570
  -> ...
  -> FUN_007b3f40
  -> FUN_007b4110
  -> ...
  -> FUN_007b2270
```

Phase 685 does **not** claim:

- complete `FUN_00763570` behavior; its remaining producer inputs stay external;
- adjacency between any of the four static anchors;
- implementation of intervening local work inside `FUN_00765470`;
- complete `FUN_00765470` semantics;
- complete retail two-half-step state refresh semantics across repeated solver
  passes;
- rendered-frame cadence, input ownership, or scene/vehicle bootstrap;
- closure of the Phase 680 machine scalar-production gate for `FUN_007afdd0`.

The report therefore keeps:

```text
phase679_join_reused = true
intervening_local_work_modeled = false
complete_fun_00765470_semantics = false
```
