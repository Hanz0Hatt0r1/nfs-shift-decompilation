# Phase 744 — selected `FUN_00765c40` collision-output handoff

Phase 744 makes the already-recovered `FUN_007b0710` result explicit at the selected BMW `FUN_00765c40` boundary. It does **not** internalize the collision/world provider that produces the result.

## PC retail order

The PC retail caller `FUN_00765c40` constructs the existing seven-double query record and calls `FUN_007b0710`. The result immediately controls caller state:

```text
returned pointer -> HDVehicle+0x38dc
hit  -> HDVehicle+0x38e0 = original_world_y - returned_contact_height
miss -> HDVehicle+0x38e0 = HDVehicle+0x38e8
```

The following contact stage `FUN_00766510` clamps `HDVehicle+0x38e0` to `[0, HDVehicle+0x38e8]` before its later response arithmetic.

## Result contract `/4`

`SHIFT.Fun00765c40ExternalPassResult/4` preserves the historical first three fields and appends an optional typed `CollisionQueryOutput`:

```text
load_terms
query_input
returned_cache_handle
query_output
```

Generic historical fixtures may leave the output absent. On the selected BMW path, identified by the native Phase739 pre-call world position, the output is mandatory.

Validation requires that the output query record belongs to the exact typed query input, hit/miss-only fields are consistent, cache-reuse state agrees with the incoming cache and returned handle, and the source-visible `returned_cache_handle` write matches `CollisionQueryOutput.returned_handle`.

## Native `+0x38e0` handoff

`SHIFT.Fun00766510QueryScalarHandoff/1` composes already-native helpers:

1. `project_fun_00765c40_query_input_scalar()` reproduces the caller `HDVehicle+0x38e0` hit/miss projection;
2. `clamp_fun_00766510_query_scalar()` reproduces the first `FUN_00766510` clamp to `[0,+0x38e8]`.

The helper is deliberately not yet wired through `NativeVehicleProviderSession`. That session/API change is Phase745.

## Relation to Phases 742–743

Phase742 closes the primary response-vector application:

```text
FUN_007551e0 result
-> FUN_007aefb0 with selected BODY0 +0xd4
-> FUN_007baa70 with selected BODY0 and HDVehicle+0x38f0
```

Phase743 closes the selected owner of the application point as the existing Phase727 `body_rotated_local` scratch. Phase744 narrows the earlier collision-result/scalar handoff feeding the still-external remainder of `FUN_00766510`.

## Provider frontier

The active provider count remains **7**. Selected BMW query world position, persistent `+0x38dc` cache state, exact selected `+0x38e8` fallback, application-point owner and now the typed collision result are no longer opaque. Collision/world lookup execution, remaining `FUN_00765c40` side effects and the incomplete remainder of `FUN_00766510` remain external.

## Next slice

Phase745 should carry the selected per-pass `CollisionQueryOutput` through `NativeVehicleProviderSession` at the recovered anchor order and supply the native `+0x38e0/+0x38e8` handoff plus the Phase743 application point to the still-external contact-response remainder. Provider count must remain seven unless the complete callback can be removed without dropping caller configuration, auxiliary scheduling, diagnostics or conditional branches.
