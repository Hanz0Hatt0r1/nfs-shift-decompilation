# Phase 745 — selected BMW `FUN_00766510` session handoff

Phase745 threads already-proven selected-session state into the still-external remainder of `FUN_00766510` without moving that remainder earlier or claiming it native.

## Inputs now owned before the callback

The selected BMW path no longer allows the residual `contact_response` provider to invent or independently source:

- the `FUN_007b0710` collision result produced by the immediately preceding residual `FUN_00765c40` pass;
- the caller-visible `HDVehicle+0x38e0` hit/miss scalar derived from that result;
- the selected `HDVehicle+0x38e8` value reused as the first `FUN_00766510` upper clamp;
- the clamped scalar after the source-visible `[0,+0x38e8]` branch sequence;
- the same-pass `HDVehicle+0x38f0` primary application point proven by Phase743.

The first four values are carried by `SHIFT.Fun00766510QueryScalarHandoff/1`. The application point is the existing Phase743 alias of Phase727 `body_rotated_local`.

## Runtime order

`NativeVehicleProviderSession` preserves the recovered anchor ordering:

```text
current BODY observer
-> residual FUN_00765c40
-> validate/capture FUN_007b0710 output and cache result
-> prepare typed FUN_00766510 input
-> FUN_00758b50 wheel_update
-> residual FUN_00766510 contact_response
```

The typed input is prepared immediately after `FUN_00765c40` because that is when the exact query output is available, but it is not consumed until the existing `contact_response` anchor executes after `wheel_update`.

## Selected BMW versus compatibility fixtures

The selected BMW domain remains identified by the already-proven 11-BODY layout used by Phases739–744. On that path, both the query-scalar handoff and application point are mandatory and validation fails closed if either is missing.

Historical two-BODY tests are not reinterpreted as the selected BMW session. They receive an empty `Fun00766510ExternalPassInput` and may continue to use one-argument compatibility callbacks. This compatibility bridge is deliberately scoped to tests/older generic harnesses and does not relax the selected-session validation.

## What remains external

This phase does not remove `NativeVehicleContactResponseProvider`. Phase742 already closes the primary response-vector application, and Phase664 closes the two-record auxiliary helper pair, but complete `FUN_00766510` still includes additional caller/configuration fields, conditional paths, `+0x40a0/+0x40a8/+0x40b0` state/accumulation, auxiliary scheduling/input ownership, and other state writes.

Therefore the active top-level provider frontier remains **7**. Reducing it to 6 is only valid once the residual `contact_response` callback itself is eliminated.
