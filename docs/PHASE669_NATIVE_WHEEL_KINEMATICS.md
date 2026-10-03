# Phase 669 — native `FUN_00758b50` wheel-kinematics boundary

Phase 669 ports the executable, source-backed part of Phase 364 `FUN_00758b50` into `shift_runtime_physics` without inventing the still-unresolved spring-helper semantics or final response vectors.

## Four-wheel topology

Retail walks four wheel-state blocks beginning at `this + 0x848` with `0xA80` stride. The corresponding runtime objects begin at `this + 0x400` with the same stride.

The native contract freezes:

- wheel count: `4`;
- wheel-state base/stride: `0x848 / 0xA80`;
- wheel-runtime base/stride: `0x400 / 0xA80`;
- first-loop skip flag: block `+0xF8` nonzero;
- final-loop flag: block `+0x11C`;
- runtime relative offsets: reference `+0x138`, distance-error `+0x128`, stored projection `+0x130`, helper output `+0x148`.

## Pre-helper arithmetic

For each non-skipped wheel, the source-visible handoff is preserved exactly:

1. consume the already-produced three-component relative vector;
2. compute its Euclidean length;
3. reject the zero-length path rather than fabricate a direction;
4. normalize the vector;
5. compute `distance_error = reference_length - relative_length`;
6. store `-projection_input` as the caller-visible projection value;
7. preserve the exact wheel-state/runtime slot offsets.

This ends immediately before the `FUN_00755950 -> FUN_007555b0` spring-gap helper chain. Phase 365 already decodes that helper in Python/reference form, but it is not silently folded into this native phase.

## Pair adjustments

The common arithmetic for both source-visible wheel pairs is native:

```text
delta = ((left_A - left_B) - (right_A - right_B)) * scale
left_destination  += delta
right_destination -= delta
```

Frozen source topology:

- front sources `+0x928/+0x938/+0x13A8/+0x13B8`, scale `+0x2E20`, destinations `+0x948/+0x13C8`;
- rear sources `+0x1E28/+0x1E38/+0x28A8/+0x28B8`, scale `+0x2E28`, destinations `+0x1E48/+0x28C8`.

The optional `FUN_007555b0` pair-helper result remains external because its native ABI/semantics are not part of this phase.

## Final transform gate

The source-visible final-loop eligibility test is ported separately:

```text
input pointer != null && block+0x11C == 0
```

The later vector construction and its `FUN_007baa70` / `FUN_007baaf0` applications are not synthesized. This keeps the native accumulator boundary evidence-driven.

## Regression

`shift_runtime_wheel_kinematics_check` verifies:

- exact four-wheel bases, strides and field offsets;
- 3-4-12 vector normalization and exact distance/projection handoff;
- `+0xF8` skip behavior across all four slots;
- exact front/rear pair source/destination topology;
- pair-delta application;
- final transform eligibility;
- zero-vector, non-finite and overflow fail-closed paths.

`native-physics-recent` now covers Phases 656–669.

## Remaining boundary

Phase 669 does not claim a complete tyre/contact force law, does not assign physical units to the recovered fields, does not implement the missing native `FUN_007555b0` spring helper, and does not schedule `FUN_00758b50` inside `NativeRuntimeState`.

The next source-backed targets are the spring-gap helper itself, the exact final per-wheel application vectors, and outer ordering inside `FUN_0076d100` / `FUN_00770e80`. Vehicle pose integration remains blocked on the unresolved persistent BODY motion/origin/basis writers.
