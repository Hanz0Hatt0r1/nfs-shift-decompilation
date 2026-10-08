# Process 1A — reject final direct `+0x4b0` writer candidate

## BLOCKER

After the DER nested-record rejection, only `0x0076019f` remained on the literal direct-displacement `+0x4b0` surface.

## OUTPUT

Machine code at `0x0075cfb0` establishes `ESI = ECX` at function entry. The candidate at `0x0076019f` is therefore a direct `this+0x4b0` qword store for that receiver.

The entry address appears in exactly one rdata table, `PTR_FUN_00b09a68`, paired with `FUN_0076b100`. Recovered source shows `FUN_0076b060` installs that vtable on its receiver.

`FUN_0076b130` then constructs four of those objects as embedded vector elements:

```text
start  = outer+0x400
stride = 0xa80
count  = 4
ctor   = FUN_0076b060
```

So `0x0076019f` writes `element+0x4b0` on an embedded `0xa80` vtable-owned object. It is not the separately allocated `0x2b90` selected PhysicsParticipant root.

## GATES_CHANGED

- `0x0076019f`: **rejected**;
- unresolved direct-displacement candidates: **0**;
- literal direct-displacement identity surface: **complete**;
- selected participant runtime `+0x4b0` producer: **still open**;
- P1.1a/P1.1: **incomplete**;
- `contact_response` removal: **not authorized**;
- provider count: **7**.

## NEXT_STEP

Widen Process 1A to computed-address, escaped-alias, indirect-dispatch and residual bulk-copy writer paths. Do not promote P1.1a until the real runtime producer is joined or all remaining writer classes are closed.
