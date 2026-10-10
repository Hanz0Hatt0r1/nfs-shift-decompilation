# Process 1A / P1.3A — `FUN_00760d93` derived alias closure

This contract follows the positive aliases left open by the merged trampolined exact-root lifetime proof.

## Child pointers `+0x420` / `+0x424`

`FUN_00760d93` loads both child pointers from the exact wheel receiver, performs scalar/vector initialization, then calls `FUN_007538a0` with the child in ECX. `FUN_007538a0` writes scalar fields relative to the child and forwards the exact child receiver only to `FUN_007ba630`; that 430-byte callee is a complete leaf and never stores/copies/forwards the pointer. The second downstream call is `FUN_007ba7e0`, whose body derives child-relative `+0x18`, `+0xd4`, and later `+0x30` lanes rather than persisting the raw child pointer.

No path reconstructs the wheel root from either child pointer.

## Interior `wheel+0x508`

At `0x00760ea3` the function materializes `wheel+0x508`, pushes it as the first stack parameter to `FUN_007b1790`, and never uses that alias again. The complete 601-byte consumer loads the pointer into EDI and uses it as input data only; after capture there is no push, store, bare register copy, or downstream call carrying EDI.

## Interior `wheel+0x9b0`

At `0x00760f22` the function materializes `wheel+0x9b0` directly in ECX and calls `FUN_00753710`. The complete 76-byte consumer copies ECX to ESI only as its local receiver, writes scalar matrix/trigonometric fields relative to ESI, and never persists or forwards the pointer.

## Gate effect

Promoted only:

- `p13a_fun00760d93_derived_alias_subset_complete = true`.

Within this bounded surface, pointer persistence, wheel-root reconstruction, and selected-target writers are all absent. Global derived-alias, reconstructed-pointer, runtime-generated pointer-store, callbacks/indirect-entry, slot0, slot1, and aggregate P1.3 gates remain fail-closed. Provider count remains 7.

The next independent derived surface is the `FUN_00757318` interior family: `wheel+0x5e8/+0x610/+0x638/+0x6a0/+0x6c0`.
