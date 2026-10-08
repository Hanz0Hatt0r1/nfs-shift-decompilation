# Process 2 P2.4 — residual producer promotion gate

## BLOCKER

`SHIFT.Fun00765c40ResidualProducerHandoff/2` separates producer families and records which families a provider actually supplied. That solves transport granularity, but `present` is not the same as `proven`.

`SHIFT.Fun00765c40ResidualProducerPromotionGate/1` separated presence from proof with boolean authorization bits. A bare boolean is still too weak for future source-backed integration because it can be set without naming the proof contract it is supposed to represent.

## OUTPUT

`SHIFT.Fun00765c40ResidualProducerPromotionGate/2` replaces anonymous boolean authorization with eight named proof receipts:

```text
Fun00765c40ResidualProducerProofMask.proof_contract_ids[8]
```

Every entry defaults empty. An effective-present producer family is authorized only when its corresponding receipt contains a non-empty proof contract ID.

`set_fun_00765c40_residual_producer_family_proven()` now requires the exact contract ID used to justify that family. Empty IDs fail closed.

`validate_fun_00765c40_residual_producer_promotion()` enforces:

- every effective-present handoff family must have a non-empty named independent-proof contract;
- absent `/2` families do not require proof and remain untouched;
- historical `/1` all-family behavior therefore requires eight named proof receipts;
- already-proven stage invariants are validated before promotion.

`apply_proven_fun_00765c40_residual_producer_handoff()` remains the safe future apply path: it validates the named proof receipts first, then delegates to the selective `/2` overlay.

## RECEIPT IS NOT EVIDENCE

A non-empty receipt is structural authorization supplied by a caller that has already consumed a concrete Process 1/source proof. The receipt is **not itself evidence** and does not establish that the named contract is applicable, current, or sufficient. The named contract remains the authority.

This slice does not populate any production receipt and does not wire the gate into the active session. Current production authorized-family count remains zero.

## GATES

- all nine producer/owner blockers remain open;
- provider witness remains non-authoritative;
- anonymous boolean authorization is no longer accepted by the active promotion API;
- no producer formula is reconstructed;
- lower scene query remains external at `0x00c133ac`, vtable `+0x1c0`;
- top-level `FUN_00765c40` provider remains present;
- external provider count remains **7**;
- complete internalization remains false.

## NEXT STEP

When Process 1 closes one producer/owner proof, Process 2 can bind exactly that family to the exact proof contract ID, compare the captured `/2` witness against independent native reconstruction, and only then route that family through the proof-gated apply path. Unresolved sibling families remain untouched.
