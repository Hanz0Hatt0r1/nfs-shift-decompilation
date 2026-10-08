# Process 1B — manager `+0x374` vptr receiver rejections

## Scope

The corrected `SHIFT.HDVehicle64e8Manager374LiteralStoreInventory/1` worklist leaves 20 actionable literal `[base+0x374]` stores after inheriting three already-merged negative sites. Receiver identity must be proven rather than inferred from the numeric displacement.

The exact Participants Manager vptr is `0x00ab916c`. Site `0x005ded7e` is intentionally excluded because corrected inventory PR #1670 already inherits its separate allocation-size rejection.

## Same-body receiver vptr rejections

Six sites are rejected because retail machine code captures the entry receiver and assigns a non-Participants-Manager vptr to the same destination base before its `+0x374` write:

- `0x0074874b` / `FUN_00748280`: `ESI=ECX`; vptr `0x00b07938`.
- `0x008169c3` / `FUN_008167f0`: `ESI=ECX`; construction vptrs `0x00b1e270`, `0x00aaa9a0`, `0x00b16158`.
- `0x00833972` / `FUN_00833760`: `EBX=ECX`; vptrs `0x00b18bc8` then `0x00b190a8`.
- `0x00844343` / `FUN_00844320`: `ESI=ECX`; vptr `0x00b190a8`.
- `0x00844b67` / `FUN_00844a20`: `ESI=ECX`; vptr `0x00b190a8`.
- `0x00d7f104` / `FUN_00d7f040`: `ESI=ECX`; vptr `0x00ac1fc4`.

Every listed vptr is distinct from `0x00ab916c`.

## Unique vtable-dispatch rejection

`FUN_008446a0` contains three literal `+0x374` stores at `0x008446cb`, `0x008446e3`, and `0x008446f8`, all through `ESI` after `0x008446a9 mov esi,ecx`.

Its machine address `0x008446a0` has exactly one function-pointer occurrence in the entire retail PE: `.rdata` address `0x00b19144`, which is vtable `0x00b190a8 + 0x9c`. There are zero direct CALL references to `FUN_008446a0`. Therefore its statically registered receiver domain is the `0x00b190a8` vtable, not Participants Manager `0x00ab916c`, and all three stores are rejected.

## Boundary

The nine newly rejected sites reduce the corrected actionable literal writer worklist from 20 to 11. The remaining 11 require owner/caller provenance, including embedded-child and copy/state families. Computed-address writes remain outside this contract.

The manager `+0x374 -> HDVehicle+0x4330` identity join, literal `0x004b86cf`, P1.3 completion, and provider removal remain fail-closed. Provider count remains 7.
