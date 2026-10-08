# Process 1B — Participants Manager vslot +0x24 EAX-residue surface

## Scope

This slice adjudicates one runtime/opaque-return candidate left after the static/constant reconstruction closures: `FUN_004d1640`, which can return with the exact Participants Manager root still resident in `EAX` after a local manager write.

PC retail 1.02 machine transfer is authoritative. The Ghidra SQLite export is navigation-only.

## Object and dispatch identity

`FUN_004d1210` installs vptr `0x00ac1860` at object offset `+0x0`. Slot `+0x24` is cell `0x00ac1884`, whose target is `FUN_004d1640`.

The exact runtime owner is rooted at `FUN_00467e50`: `0x00468998` allocates `0x18` bytes, `0x004689a8` calls `FUN_004d1210`, and `0x004689b1` stores the constructed object at `outer+0xc4c`.

The exact slot invocation is then visible in `FUN_004b7550`: it loads global outer root `0x00bc185c`, loads `outer+0xc4c`, reads its vtable, reads slot `+0x24`, and calls it at `0x004b75bc`.

## EAX residue

Inside `FUN_004d1640`, `0x004d16e9` calls `FUN_00489ad0`. The returned manager root is used locally at `0x004d16f0` to clear byte `manager+0x434`. The function then returns without reloading `EAX`, so the manager root can remain as incidental register residue.

That residue does not survive the exact runtime consumer. Immediately after the indirect slot call, `0x004b75be` executes `mov al,1`, changing the low byte of `EAX`, and the caller returns at `0x004b75c6`. Therefore the exact 32-bit Participants Manager root is not exported by this dispatch path.

## Adjudication

The exact `outer+0xc4c -> vtable+0x24 -> FUN_004d1640` path is closed-negative as an alternate exact manager-root producer. It does not introduce a new value at manager `+0x374`.

This does not close `FUN_0045b130` at vtable `0x00ab5644+0x0c`, other runtime-created aliases, or unrelated indirect/external initialization. The `0x004b86cf` candidate remains fail-closed and provider count remains 7.
