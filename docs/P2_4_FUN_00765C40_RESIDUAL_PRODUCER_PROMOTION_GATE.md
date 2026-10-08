# Process 2 P2.4 — residual producer promotion gate

## BLOCKER

`SHIFT.Fun00765c40ResidualProducerHandoff/2` separates producer families and records which families a provider actually supplied. That solves transport granularity, but `present` is not the same as `proven`.

A future runtime path must not feed a captured family into `SHIFT.Fun00765c40ComposedResidualExecutor/1` merely because the provider marked it present. Process 2 still needs an independent source-backed ownership/equivalence proof for that family.

## OUTPUT

`SHIFT.Fun00765c40ResidualProducerPromotionGate/1` adds a separate eight-bit proof mask:

```text
Fun00765c40ResidualProducerProofMask.independently_proven[8]
```

The default mask is all false.

`validate_fun_00765c40_residual_producer_promotion()` enforces:

- every effective-present handoff family must have the matching independent-proof bit;
- absent `/2` families do not require proof and remain untouched;
- historical `/1` all-family behavior therefore requires all eight proof bits;
- already-proven stage invariants are validated before promotion.

`apply_proven_fun_00765c40_residual_producer_handoff()` is the safe future apply path: it validates the proof gate first, then delegates to the selective `/2` overlay.

## PROOF MASK IS NOT EVIDENCE

A `true` bit is structural authorization supplied by a caller that has already consumed a concrete Process 1/source proof. The bit itself does not establish ownership or equivalence and must never be used to invent a missing proof.

This PR does not set any proof bit in production and does not wire the gate into the active session.

## GATES

- all nine producer/owner blockers remain open;
- provider witness remains non-authoritative;
- no producer formula is reconstructed;
- lower scene query remains external at `0x00c133ac`, vtable `+0x1c0`;
- top-level `FUN_00765c40` provider remains present;
- external provider count remains **7**;
- complete internalization remains false.

## NEXT STEP

When Process 1 closes one producer/owner proof, Process 2 can set exactly that family’s proof bit, compare the captured `/2` witness against independent native reconstruction, and only then route that family through the proof-gated apply path. Unresolved sibling families remain untouched.
