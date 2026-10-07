# Phase 742 — native FUN_00766510 primary response application

Phase 742 closes the specific source-backed application path that remained open after Phases 657, 663 and 667. It does **not** claim the complete `FUN_00766510` caller is native yet.

## PC retail sequence

The authoritative PC retail block is decompiler lines `759686..759695`, corresponding to machine span `0x00766f9f..0x00767046` (SHA-256 `ea0d7c2fb2f33101808f9ad997867c724476fea62bc0ed60f6af0023471f1546`).

The sequence is:

```text
FUN_007551e0(this+0x3950, ..., response_vector, auxiliary_response)
FUN_007aefb0(BODY+0xd4, response_vector, transformed_response)
FUN_007baa70(BODY, this+0x38f0, transformed_response)
FUN_00753650(caller_reference_vector, transformed_response, cross_delta)
this+0x40a0/+0x40a8/+0x40b0 += cross_delta
auxiliary_accumulator += auxiliary_response
```

No physical names are assigned to `this+0x38f0`, the caller reference vector, the `+0x40a0` family, or the auxiliary lanes.

## Native composition

`execute_fun_00766510_primary_response_application()` reuses only already-proven native primitives:

- `FUN_007551e0` output contract from `SHIFT.NativeWheelContactResponse/1`;
- exact x87-shaped `FUN_007aefb0` transform through `transform_fun_007aefb0_refresh()`;
- `FUN_007baa70` positive BODY accumulator primitive from `SHIFT.NativeBodyAccumulatorPrimitives/1`;
- exact `FUN_00753650(left,right) = left × right` ordering;
- source-order lane accumulation for the `+0x40a0` family and caller-local auxiliary vector.

The helper accepts all still-unproven caller state explicitly rather than synthesizing it.

## Why this is not a provider removal yet

The old frontier named two blockers for `FUN_00766510`:

1. primary response-vector application into `FUN_007baa70` was not frozen;
2. caller-state production/ownership was incomplete.

Phase742 closes blocker 1 only. The session-level `contact_response` callback remains required until the relevant caller state and remaining branches/finalization are joined source-first.

## Regression

The native check uses a non-identity BODY frame so the `FUN_007aefb0` path is observable, then verifies:

- transformed response vector;
- BODY linear and angular accumulator changes through `FUN_007baa70`;
- `FUN_00753650` cross-product ordering;
- `+0x40a0`-family accumulation;
- auxiliary-response accumulation;
- fail-closed handling of non-finite inputs.

Top-level external provider count remains **7**.
