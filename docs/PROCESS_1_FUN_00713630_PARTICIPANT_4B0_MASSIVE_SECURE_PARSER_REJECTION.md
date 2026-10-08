# Process 1A — reject `0x00607f22` from the participant `+0x4b0` frontier

## BLOCKER

After the nested-copy rejection, two direct-displacement `+0x4b0` candidates remained: `0x00607f22` and `0x0076019f`.

## OUTPUT

`0x00607f22` is not a root-relative selected `PhysicsParticipant+0x4b0` writer.

The store belongs to `FUN_006075f0`, which zeroes a `0x5e0` parser workspace and writes its parsed payload length at workspace `+0x4b0`. Retail code has one direct call to this parser at `0x0060876a`. `FUN_00608720` obtains `backing = *(state+0x128)` and passes `backing+0x410` as the parser receiver, so the candidate maps to `backing+0x8c0`, not `state+0x4b0`.

The dispatcher preserves the same geometry. `FUN_00608f80` receives the state in `EDI`; thunk `0x0048fc41` loads `ESI=[EDI+0x128]` before continuing the secure/network state machine, whose `0x00609296` branch calls `FUN_00608720` with that state. The corresponding owner family is rooted by `FUN_0060b1f9`, which installs `MassiveAdClient3::XMassiveAdClient::vftable` and owns `this+0x128`; `FUN_0060beb7` creates the global instance at `DAT_00be8618`.

The recovered parser consumer immediately uses `backing+0x8c0` / `backing+0x8c4` as parsed buffer length/data. This is secure/parser workspace state and does not join the separately allocated selected PhysicsParticipant root.

## GATES_CHANGED

- `0x00607f22`: **rejected**.
- unresolved direct-displacement candidates: **1** (`0x0076019f`).
- selected participant runtime `+0x4b0` producer: **open**.
- P1.1a/P1.1: **incomplete**.
- `contact_response` removal: **not authorized**.
- provider count: **7**.

## LIMITS

This contract does not classify or reject `0x0076019f`. That final site is genuine physics/math code in a Ghidra function-boundary gap and may still belong to participant-family state. Computed-address, escaped-alias, indirect-dispatch and residual bulk-copy surfaces stay deferred until it is resolved.

## NEXT_STEP

Recover the enclosing procedure and exact receiver identity for `0x0076019f`. Do not issue a negative claim unless its physics receiver is disproven.
