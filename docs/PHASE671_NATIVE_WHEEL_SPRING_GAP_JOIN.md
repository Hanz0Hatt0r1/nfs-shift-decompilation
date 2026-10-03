# Phase 671 — native `FUN_00758b50 -> FUN_00755950 -> FUN_007555b0` spring-gap join

Phase 671 composes the already-native Phase 669 wheel-kinematics handoff with the Phase 670 spring-gap state writes. The join is source-backed by the existing `evaluate_wheel_spring_gap()` reference oracle and does not assign physical force units or invent the unresolved x87 return consumed by `FUN_00755950`.

## Exact scalar join

Phase 669 freezes, per wheel:

```text
distance_error = reference_length - relative_length
stored_projection = -projection_input
```

The recovered Phase 365/364 caller boundary then passes exactly those values into the `FUN_007555b0` state logic:

```text
displacement = distance_error
trigger_value = stored_projection
```

`execute_fun_00755950_spring_gap_join()` performs this composition and returns the Phase 670 `SpringGapStateResult`.

## Cross-contract identity gate

The native join rejects malformed records before composing them. It requires:

- wheel index in `0..3`;
- wheel-state offset equal to `0x848 + index*0xA80`;
- wheel-runtime offset equal to `0x400 + index*0xA80`;
- `distance_error == reference_length - relative_length`;
- `stored_projection == -projection_input`;
- finite kinematic scalar state.

These checks are a native admission boundary. They ensure that the Phase 669 output being fed into Phase 670 still represents the same source-visible wheel slot and scalar relationships.

## Regression

`shift_runtime_wheel_spring_gap_join_check` covers:

- a nontrivial wheel-2 kinematic fixture with length 13, reference 15, displacement 2 and trigger 2;
- the positive-over-negative crossing path through Phase 670;
- a non-crossing path with no invented clear writes;
- rejection of mismatched wheel topology;
- rejection of tampered distance-error and projection handoffs;
- non-finite spring-state rejection.

`native-physics-recent` is extended through Phase 671.

## Remaining boundary

The caller-side x87 value stored at runtime `+0x548` remains external and unresolved. Phase 671 does not schedule `FUN_00758b50`/`FUN_00755950` in `NativeRuntimeState`, does not invent spring-force semantics, and does not close the final `FUN_007baa70/FUN_007baaf0` application vectors.

The next higher-level evidence frontier remains `FUN_0076d100` and the two-pass `FUN_00770e80` ordering, plus static recovery of the persistent BODY motion/pose writer chain.
