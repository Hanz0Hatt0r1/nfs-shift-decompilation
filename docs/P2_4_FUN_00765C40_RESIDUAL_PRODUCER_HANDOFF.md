# Process 2 P2.4 — residual producer handoff

## BLOCKER

`SHIFT.Fun00765c40ComposedResidualExecutor/1` executes the recovered residual pass in retail order, but the eight unresolved pure-data producer families cannot all be proven at once.

`SHIFT.Fun00765c40ResidualProducerHandoff/1` grouped those families, but it had no per-family presence state. Any handoff therefore behaved as if all eight payload families were meaningful, and `apply_fun_00765c40_residual_producer_handoff()` overwrote all eight composed inputs. That makes incremental proof promotion unsafe: proving one producer family could default-overwrite seven still-unresolved inputs.

## OUTPUT

`SHIFT.Fun00765c40ResidualProducerHandoff/2` preserves the eight historical `/1` payload fields as an unchanged prefix and appends explicit family presence:

- `family_presence_explicit`;
- `family_present[8]`.

The eight families remain:

- wheel-plane payloads;
- the exact-width `HDVehicle+0x98` wheel-state source bits;
- `FUN_007584f0` computed payloads;
- wheel-pair payloads;
- contact-array payloads;
- contact BODY predicate/vector entries;
- bounded state-tail predicate/payloads;
- optional BODY sweep predicate/vector entries.

### Compatibility rule

When `family_presence_explicit == false`, the handoff preserves historical `/1` behavior: all eight families are treated as present and are copied exactly as before.

When explicit mode is enabled, only entries marked in `family_present[8]` may overlay `Fun00765c40ComposedResidualInputs`. Absent families preserve the caller's existing composed input values.

Known-invariant validation follows the same rule. The already-proven finite contract for `FUN_007584f0` is checked only when `PersistentWrite` is present. Opaque qword payloads and unresolved BODY vectors are not reinterpreted or range-restricted.

## EXCLUDED BY DESIGN

The handoff still does not contain:

- current BODY bytes or selected world position — native-owned;
- query cache or selected `+0x38e8` fallback — native-owned;
- initial BODY accumulator state — persistent native BODY state;
- wheel-job queue execution or post-queue `+0x738` reads — still an explicit scheduling seam because `FUN_0075cfb0` arithmetic/side effects are not closed;
- lower scene-query behavior — still external at `0x00c133ac`, vtable `+0x1c0`.

## GATES

This slice changes transport granularity, not producer ownership. It does not reconstruct a formula, remove the top-level provider, or decrement the external provider count. Complete `FUN_00765c40` internalization remains false and provider count remains 7.

`Fun00765c40ExternalPassResult/5` and the session capture continue to treat the handoff as a non-authoritative witness.

## NEXT STEP

As Process 1 closes individual producer/owner proofs, mark only those corresponding `/2` families present and validate them against independent native reconstruction. A family may feed the composed executor without default-overwriting unresolved siblings. Provider removal remains fail-closed until the remaining producer/owner frontier is empty.
