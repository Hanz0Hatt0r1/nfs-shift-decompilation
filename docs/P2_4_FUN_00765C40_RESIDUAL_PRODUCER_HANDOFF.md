# Process 2 P2.4 — residual producer handoff

## BLOCKER

`SHIFT.Fun00765c40ComposedResidualExecutor/1` already executes the recovered residual pass in retail order, but eight unresolved pure-data producer families are still supplied directly through `Fun00765c40ComposedResidualInputs`. Keeping them scattered makes the future top-level provider/session handoff ambiguous and risks mixing them with state that is already native-owned.

## OUTPUT

`SHIFT.Fun00765c40ResidualProducerHandoff/1` groups only those unresolved pure-data families:

- wheel-plane payloads;
- the exact-width `HDVehicle+0x98` wheel-state source bits;
- `FUN_007584f0` computed payloads;
- wheel-pair payloads;
- contact-array payloads;
- contact BODY predicate/vector entries;
- bounded state-tail predicate/payloads;
- optional BODY sweep predicate/vector entries.

`apply_fun_00765c40_residual_producer_handoff()` copies exactly those families into a composed input while preserving all caller-owned state and external behavior seams.

## EXCLUDED BY DESIGN

The handoff does not contain:

- current BODY bytes or selected world position — native-owned;
- query cache or selected `+0x38e8` fallback — native-owned;
- initial BODY accumulator state — persistent native BODY state;
- wheel-job queue execution or post-queue `+0x738` reads — still an explicit scheduling seam because `FUN_0075cfb0` arithmetic/side effects are not closed;
- lower scene-query behavior — still external at `0x00c133ac`, vtable `+0x1c0`.

This separation prevents a future provider handoff from accidentally taking ownership back from already-native state.

## GATES

This slice is structural only. It does not reconstruct any producer formula, change the active `Fun00765c40ExternalPassResult`, remove the top-level provider, or decrement the external provider count. Complete `FUN_00765c40` internalization remains false and provider count remains 7.

## NEXT STEP

Thread the pure-data handoff through the top-level `FUN_00765c40` result/session boundary as a typed witness. It must remain non-authoritative until the selected provider can supply the source-backed values. Wheel-job execution and lower scene-query behavior remain separate external seams until independently closed.
