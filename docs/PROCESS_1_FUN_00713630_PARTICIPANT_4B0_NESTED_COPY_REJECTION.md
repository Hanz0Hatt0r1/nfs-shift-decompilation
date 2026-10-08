# Process 1A — reject `0x00487d2d` nested-copy `+0x4b0` writer

## BLOCKER

After the receiver-size rejection, three direct-displacement `+0x4b0` candidates remain. `0x00487d2d` is inside `FUN_004876f0`.

## OUTPUT

The retail static-reference surface for `FUN_004876f0` has exactly two rel32 calls, no rel32 jumps to the entry, and no literal image reference to the function address.

Both calls are inside `FUN_0048bbc0`:

- `0x0048bc90`: `ECX = outer+0x110`, so callee `+0x4b0` maps to `outer+0x5c0`;
- `0x0048bca2`: `ECX = outer+0xa00`, so callee `+0x4b0` maps to `outer+0xeb0`.

Therefore the direct store at `0x00487d2d` cannot be the root-relative selected PhysicsParticipant `+0x4b0` storage at either actual receiver root. No subsystem/class semantic label is needed.

The candidate machine window, caller machine window, and recovered `FUN_004876f0` source body are hash-pinned.

## GATES_CHANGED

- `0x00487d2d`: **rejected**;
- unresolved direct-displacement candidates: **2**;
- selected participant runtime `+0x4b0` producer: **open**;
- P1.1a/P1.1: **incomplete**;
- `contact_response` removal: **not authorized**;
- provider count: **7**.

## LIMITS

This closes the visible retail static reference surface for `FUN_004876f0`; it does not classify the two remaining direct sites or any computed/escaped-alias/indirect/residual-bulk writer path.

## NEXT_STEP

Adjudicate `0x00607f22` and `0x0076019f` before widening beyond direct-displacement stores.
