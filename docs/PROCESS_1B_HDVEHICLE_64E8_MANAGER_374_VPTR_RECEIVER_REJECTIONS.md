# Process 1B — manager `+0x374` vptr receiver rejections

## Scope

`SHIFT.HDVehicle64e8Manager374LiteralStoreInventory/1` leaves 23 literal `[base+0x374]` stores whose receiver identity must be proven rather than inferred from the numeric displacement.

This slice rejects seven sites where retail machine code assigns a non-Participants-Manager vptr to the **same receiver register** that later forms the `+0x374` destination.

The exact Participants Manager vptr is `0x00ab916c`.

## Rejected receiver identities

- `0x005ded7e` / `FUN_005dec70`: `ESI=ECX`; same receiver gets vptr `0x00adee38`.
- `0x0074874b` / `FUN_00748280`: `ESI=ECX`; same receiver gets vptr `0x00b07938`.
- `0x008169c3` / `FUN_008167f0`: `ESI=ECX`; same receiver is successively assigned `0x00b1e270`, `0x00aaa9a0`, then `0x00b16158` before the target store.
- `0x00833972` / `FUN_00833760`: `EBX=ECX`; same receiver gets `0x00b18bc8` then `0x00b190a8`.
- `0x00844343` / `FUN_00844320`: `ESI=ECX`; same receiver gets `0x00b190a8` immediately before the `+0x374` lifecycle clear.
- `0x00844b67` / `FUN_00844a20`: `ESI=ECX`; same receiver gets `0x00b190a8` before the copied state fields including `+0x374`.
- `0x00d7f104` / `FUN_00d7f040`: `ESI=ECX`; same receiver gets `0x00ac1fc4` before its broad field initialization.

Every listed vptr is distinct from `0x00ab916c`. Therefore these seven stores are not writes to Participants Manager `manager+0x374`.

## Boundary

This reduces the literal writer receiver-provenance worklist from 23 to 16 sites. It does not classify the remaining 16 and does not cover computed-address writes that reach `+0x374` without a literal displacement.

The manager `+0x374 -> HDVehicle+0x4330` identity join, literal `0x004b86cf`, P1.3 completion, and provider removal remain fail-closed. Provider count remains 7.
