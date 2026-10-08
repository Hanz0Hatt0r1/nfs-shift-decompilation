# Process 1A — reject `0x00832f46` by receiver size contradiction

## BLOCKER

After the two account/service record rejections, four direct-displacement `+0x4b0` candidates remain. `0x00832f46` in `FUN_00832a80` writes one of them.

## OUTPUT

The candidate is rejected without assigning a semantic class name.

At `0x00832f46`, `FUN_00832a80` writes `[ESI+0x4b0]`. In the same function and on the same receiver register, `0x00832fe1` computes `LEA EDI,[ESI+0x3960]`. The recovered source expresses the same access as `piVar17 = param_1 + 0xe58`; with four-byte elements, that is byte offset `0x3960`.

The selected PhysicsParticipant root is independently fixed as a separately allocated `0x2b90` object. A receiver whose concrete layout is directly accessed at `+0x3960` cannot be that selected PhysicsParticipant object. Numeric equality of the earlier `+0x4b0` displacement therefore does not establish identity.

The candidate write window, far-access window, and complete recovered `FUN_00832a80` body are hash-pinned.

## GATES_CHANGED

- `0x00832f46`: **rejected**;
- same-receiver size contradiction: **closed**;
- unresolved direct-displacement candidates: **3**;
- selected participant runtime `+0x4b0` producer: **open**;
- P1.1a/P1.1: **incomplete**;
- `contact_response` removal: **not authorized**;
- provider count: **7**.

## LIMITS

This proof does not name the candidate object's subsystem and rejects only `0x00832f46`. The remaining three direct sites and computed/escaped-alias/indirect/residual-bulk paths remain open.

## NEXT_STEP

Adjudicate the remaining three direct-displacement `+0x4b0` sites by exact receiver provenance.
