# Phase 742 — selected `FUN_00765c40` collision-output handoff

Phase 742 makes the already-recovered `FUN_007b0710` result explicit at the selected BMW `FUN_00765c40` boundary. It does **not** internalize the collision/world provider that produces the result.

## PC retail order

The PC retail caller `FUN_00765c40` constructs the existing seven-double query record and calls `FUN_007b0710`. The result then immediately controls caller state:

```text
returned pointer -> HDVehicle+0x38dc
hit  -> HDVehicle+0x38e0 = original_world_y - returned_contact_height
miss -> HDVehicle+0x38e0 = HDVehicle+0x38e8
```

The next contact stage `FUN_00766510` clamps `HDVehicle+0x38e0` to the inclusive interval `[0, HDVehicle+0x38e8]` before its later response arithmetic.

## Result contract `/4`

`SHIFT.Fun00765c40ExternalPassResult/4` preserves the historical first three fields and appends an optional typed `CollisionQueryOutput`:

```text
load_terms
query_input
returned_cache_handle
query_output
```

For generic historical fixtures the output can remain absent. On the selected BMW path, identified by the native Phase739 pre-call world position, the output is mandatory.

Validation proves that:

- the output query record belongs to the exact typed query input;
- hit output carries contact height and returned handle consistently;
- miss output does not invent hit-only fields;
- the cache-reuse bit agrees with the incoming cache handle and returned handle;
- the source-visible `returned_cache_handle` write agrees with `CollisionQueryOutput.returned_handle`.

This removes the ability of the selected residual provider to hide its `FUN_007b0710` hit/miss/contact-height/cache-output state while keeping the actual world/collision lookup implementation external.

## Native `+0x38e0` handoff

`SHIFT.Fun00766510QueryScalarHandoff/1` composes already-native helpers:

1. `project_fun_00765c40_query_input_scalar()` reproduces the caller `HDVehicle+0x38e0` value;
2. `clamp_fun_00766510_query_scalar()` reproduces the first `FUN_00766510` clamp to `[0,+0x38e8]`.

Focused regression covers:

- cache-reused hit;
- non-reused hit;
- upper clamp;
- lower clamp;
- miss fallback;
- rejection of a hidden selected collision output;
- rejection of an output record belonging to another query.

The helper is deliberately **not** wired through `NativeVehicleProviderSession` in this phase. That keeps the result-contract change separate from the next provider-API change.

## Provider frontier

The active provider count remains **7**. The current frontier is refreshed to Phase742:

- selected BMW query world position is native-owned from Phase739;
- `+0x38dc` cache lifetime is native-owned from Phase740;
- selected `+0x38e8` fallback is native-owned from Phase741;
- selected `CollisionQueryOutput` is now typed and mandatory;
- collision/world provider execution and remaining `FUN_00765c40` side effects are still external;
- `FUN_00766510` remains an external contact-response boundary.

## Next slice

Phase743 should store/carry the selected per-pass `CollisionQueryOutput` in `NativeVehicleProviderSession`, compute the native `+0x38e0`/clamp handoff at the recovered anchor order, and pass that typed input into the still-external `FUN_00766510` provider. It must not claim complete `FUN_00766510` internalization: primary BODY application, the `+0x40a0/+0x40a8/+0x40b0` accumulator and additional conditional branches remain distinct evidence targets.
