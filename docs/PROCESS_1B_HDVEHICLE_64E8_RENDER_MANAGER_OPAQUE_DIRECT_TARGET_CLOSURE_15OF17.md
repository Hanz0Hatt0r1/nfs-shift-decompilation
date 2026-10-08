# Process 1B — render-manager opaque direct-target closure, 15/17

## Scope

`SHIFT.PlayerVehicleRenderManagerReceiverTransferFrontier/2` bounds the direct exact-root receiver branch to 17 retail targets. Merged #1654/#1655 explicitly close seven. This slice closes eight more and leaves only the two getter-like targets `0x00489ad0` and `0x00493fb0` pending a complete caller/post-call residue inventory.

PC retail 1.02 machine transfer is authoritative. Decompiled source is navigation-only.

## Entry-clobber / ignored-receiver targets

- `0x00449630`: all three pinned exact-root receiver callsites (`0x004be25d`, `0x004bf71b`, `0x004c06e6`) carry the root in `EDX`. `0x00449639 mov edx,[ebp+0xc]` overwrites it before forwarding.
- `0x00459140`: immediately jumps through `0x0045b51b`, which replaces working state with fixed global `0x00bc8e30`; entry ECX/EDX are never consumed.
- `0x0045abe0`: calls `0x00886980`, which does not read entry ECX, then `0x0045abe5 lea ecx,[eax+0x78]` destroys the residual root before the tail transfer.
- `0x00468ed0`: at the exact-root callsite `0x004d6015` the root arrives in ECX. The target does not read/save it before `0x00468ee9 mov ecx,0x00bbc600`.

## Field-base / derived-receiver targets

- `0x0045bfc0 -> 0x00d51560`: exact root is captured in EDI, used only to inspect/load `root+0xc`, and is never stored, returned, or re-forwarded. This leaf was already second-hop-classified by #1654; this slice counts its independent direct-target entry.
- `0x0045cc50 -> 0x00d517b0`: exact root is captured in EBX and used only to derive `root+0x520`, `root+0x780`, `root+0x9e0`, and byte field `root+0x19`. No exact-root transfer occurs.
- `0x00462400`: keeps root in ESI, sends it to `0x0045e6e0`, and every surviving path either replaces ECX with a singleton/getter result, passes root to the already-bounded `0x0045abe0`, or enters `0x0045abf0`, which does not read/save entry root before its own getter path. Final indirect dispatch receiver is global `[0x00c26058]`, not root.

## Address-of-local output target

`0x0045db50 -> 0x00d51bd0` materializes the exact root at `[ebp-0x4]` and passes `&local` through `0x0045b720 -> 0x004651a0 -> 0x004bb4f0 -> 0x00d77800`. The first dereference of that output slot is `0x00d77868 mov dword ptr [esi],0`; the original root is erased before any read. Later replacement pointers are not promoted to the original root.

## Adjudication

These eight targets plus the seven explicit closures from merged #1654/#1655 bring the bounded direct-target opaque-alias surface to **15/17**. The two remaining targets are deliberately not closed here because their getter hot paths can physically preserve residual ECX even though they return unrelated singleton roots in EAX. Their complete exact-root caller/post-call residue surface must be pinned first.

Global external/unknown-origin aliases, two-unknown-origin `HDVehicle+0x4330` reconstruction, the manager `+0x374 -> HDVehicle+0x4330` join, literal `0x004b86cf`, P1.3 completion, and provider removal remain fail-closed. Provider count remains 7.
