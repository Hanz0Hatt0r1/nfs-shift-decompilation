# Phase 665 — native FUN_00758ad0 wheel-contact factor

Phase 665 ports the instruction-stream-exact `FUN_00758ad0` helper and its four-record `FUN_00765c40` storage topology into `shift_runtime_physics`.

## Exact helper arithmetic

For the source scalar input and runtime threshold `DAT_00c10f94`, the native implementation preserves the Phase 369 sequence:

1. `pre_clamp = abs(input) - threshold * 0.5`;
2. clamp `pre_clamp` to `[0, 6]`;
3. `angle = clamped * 3.1415927410125732 / 6.0`;
4. evaluate cosine, matching the source path that reaches x87 `FCOS` through `FUN_00900b10`;
5. compute `cosine * 0.02500000037252903 + 0.9750000238418579`;
6. round the final value through a 32-bit float conversion before returning it as the native contract value.

The threshold global remains an input. This phase does not replace it with a guessed constant.

## FUN_00765c40 storage topology

The caller-visible four-wheel layout is frozen as:

```text
wheel_count   = 4
stride        = 0x150
previous_base = 0xa70
factor_base   = 0xa78
```

When the external helper gate is enabled, one factor is computed for each projected source value. When disabled, the source-visible factor is exactly `1.0`.

The previous/reference slot receives the supplied frame reference when the recovered frame-equality condition is true, otherwise zero. Physical names and units remain intentionally unresolved.

## Scope

This phase does not perform the `FUN_007b0710` collision query and does not assign suspension/contact/force semantics to the projected scalar or stored factor. It only ports arithmetic and storage relationships already closed in Phase 369.

Non-finite native inputs fail closed.

## Regression

`shift_runtime_wheel_contact_factor_check` covers:

- zero and six-unit clamp endpoints;
- the midpoint/cosine path;
- threshold subtraction before clamping;
- exact final float32 rounding boundary;
- four-wheel source order and `0x150` storage stride;
- frame-reference branch;
- disabled-factor `1.0` path;
- non-finite rejection.

`native-physics-recent` now executes and verifies Phases 656–665.

## Next boundary

The next source-backed native target is the Phase 370 `FUN_00765c40` → `FUN_007b0710` query record: seven doubles, cache-handle propagation, hit/miss normal behavior, and the caller's `+0x38dc/+0x38e0` observable result boundary. The transform producing the query world position should remain external until its exact caller mapping is proven.
