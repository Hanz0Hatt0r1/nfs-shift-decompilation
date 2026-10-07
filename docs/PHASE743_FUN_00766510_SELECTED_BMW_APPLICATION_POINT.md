# Phase 743 — selected BMW `FUN_00766510` application-point ownership

Phase 743 proves that the selected BMW query-response application point read by `FUN_00766510` at `HDVehicle+0x38f0/+0x38f8/+0x3900` is not a separate producer. It is the exact BODY-rotated local sample already computed by `FUN_00765c40` and exposed natively by Phase727 as `Fun00765c40WorldPositionTransformResult.body_rotated_local`.

## PC source ownership

Inside `FUN_00765c40` the authoritative PC export performs:

```text
FUN_007aefb0(BODY0+0xd4, HDVehicle+0x3938, HDVehicle+0x38f0)
FUN_00753590(..., HDVehicle+0x38f0, BODY0)
```

The first call writes the f64 rotated scratch. The second call consumes it to form the origin-added collision world position but does not replace the scratch with that world position.

The later `FUN_00766510` anchor executes:

```text
pdVar7 = HDVehicle+0x38f0
...
FUN_007baa70(BODY0, pdVar7, transformed_response)
```

Phase684 already freezes the pass order as `FUN_00765c40 -> FUN_00758b50 -> FUN_00766510`, so the later response anchor consumes the same pass's stored scratch.

## Existing native owner

Phase727's `execute_fun_00765c40_world_position_transform()` already returns both stages separately:

- `body_rotated_local` — the value stored at `HDVehicle+0x38f0`;
- `world_position` — BODY0 origin plus that rotated scratch.

Phase739 composes this result from the authoritative per-pass selected BMW BODY state. Therefore Phase743 introduces only an alias:

```text
FUN_00766510 application point = Phase727 body_rotated_local
```

It deliberately does not recompute the transform and does not use `world_position`.

## Scope

This phase closes source ownership only. It does not yet change the `contact_response` callback signature or pass the owned point into the residual provider. That runtime handoff is a later bounded integration step. The top-level provider count remains seven.
