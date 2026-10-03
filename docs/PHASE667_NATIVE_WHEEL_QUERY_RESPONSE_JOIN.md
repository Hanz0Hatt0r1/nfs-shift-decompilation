# Phase 667 — native FUN_00765c40 → FUN_00766510 query/response join

Phase 667 closes the source-backed scalar boundary between the native Phase 666 collision-query contract and the native Phase 663 wheel-response path.

Phase 370 established that `FUN_00765c40` writes runtime state `+0x38e0` as:

- hit: `original_world_y - returned_contact_height`;
- miss: existing runtime fallback at `+0x38e8`.

Phase 371 established that `FUN_00766510` immediately clamps runtime `+0x38e0` to `[0, +0x38e8]` before forming its response gain. Phase 667 composes exactly those two already-native boundaries.

## Native join

`execute_fun_00765c40_to_00766510_response_join()`:

1. consumes an externally supplied `CollisionQueryOutput` from the Phase 666 provider boundary;
2. computes the caller-visible `+0x38e0` scalar through `project_fun_00765c40_query_scalar()`;
3. uses the same source `+0x38e8` value both as the miss fallback and as the upper clamp bound consumed by `FUN_00766510`;
4. forwards the scalar into `evaluate_fun_00766510_contact_response_from_body_source()`;
5. therefore preserves the Phase 663 `body+0xd4` / `body+0x18` response-input transform and existing `FUN_007551e0` quadratic response arithmetic.

The frozen source state offsets are:

```text
FUN_00765c40 / FUN_00766510 query scalar = +0x38e0
FUN_00766510 upper bound / miss fallback = +0x38e8
FUN_00766510 response gain output        = +0x39d0
```

## Provider remains external

This phase deliberately accepts `CollisionQueryOutput` rather than calling a guessed track/collision implementation. `FUN_007b0710` / `FUN_0074f560` ownership and native surface-provider execution remain separate evidence targets.

Likewise this phase does not schedule the joined path in `NativeRuntimeState`, does not assign physical names or units to `+0x38e0/+0x38e8/+0x39d0`, and does not infer vehicle pose integration.

## Regression

`shift_runtime_wheel_query_response_join_check` verifies:

- hit scalar propagation from Phase 666 into `FUN_00766510`;
- miss fallback uses the same `+0x38e8` source value as the consumer upper bound;
- a hit value above `+0x38e8` is upper-clamped;
- a negative hit value is lower-clamped to zero;
- response gain follows the existing Phase 371 arithmetic;
- the Phase 663 BODY-source transform and `FUN_007551e0` response outputs remain intact across the join.

`native-physics-recent` now executes and verifies Phases 656–667.

## Next boundary

The next safe integration target is caller orchestration around the joined wheel response and the already-native two-record auxiliary response pair. The primary `FUN_007551e0` response-vector application transform into `FUN_007baa70` remains evidence-gated and must not be guessed. Runtime scheduling should remain separate until the source-visible ownership/order of the full contact stage is frozen.
