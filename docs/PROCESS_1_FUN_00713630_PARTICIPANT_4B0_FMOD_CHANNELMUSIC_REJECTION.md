# Process 1A — reject `0x0098e583` from participant `+0x4b0` frontier

## BLOCKER

`SHIFT.Fun00713630Participant4b0RemainingDirectWorklist/1` leaves seven direct-displacement `+0x4b0` sites. `0x0098e583` in `FUN_0098e558` is one of them.

## OUTPUT

The candidate receiver is rooted to the FMOD audio object domain, not the selected PhysicsParticipant graph.

`FUN_0098e558` constructs the embedded object at `this+0x48c` through `FUN_0099dec0`, then installs `FMOD::ChannelMusic::vftable` there. The base constructor `FUN_0099dec0` itself installs `FMOD::ChannelReal::vftable`. In the same candidate function the exact direct site sets bit `0x10` in `[this+0x4b0]` and stores a backpointer at `[this+0x4dc] = this`.

Therefore the `0x0098e583` write is FMOD audio-owner state. Numeric equality with `PhysicsParticipant+0x4b0` is not an identity join.

The authoritative recovered source function is pinned at lines `1201281-1201302`, SHA-256 `54fb51bda540bffc09e3cc689d67f0dc96f716481a4f6d80861d8fe1ec3d986a`, under the already pinned retail decompiler hash.

## GATES_CHANGED

- `0x0098e583`: **rejected**;
- receiver FMOD domain: **closed**;
- unresolved direct-displacement candidates: **6**;
- selected participant runtime `+0x4b0` producer: **open**;
- P1.1a/P1.1: **incomplete**;
- `contact_response` removal: **not authorized**;
- provider count: **7**.

## LIMITS

This rejects only `0x0098e583`. It does not classify the other six direct sites and does not widen into computed-address, escaped-alias, indirect-dispatch, or residual bulk-copy paths.

## NEXT_STEP

Continue exact receiver-provenance adjudication of the remaining six direct-displacement `+0x4b0` sites.
