# Process 1B — manager `+0x374` receiver-vptr negative batch 1

## Scope

`SHIFT.HDVehicle64e8Manager374LiteralStoreInventory/1` leaves 23 literal `[base+0x374]` writes across 19 functions whose receiver identity is not yet classified. Matching displacement alone is not manager identity.

This slice rejects seven sites where retail machine code captures entry `this`, installs an explicit vptr on that exact receiver, and later writes receiver `+0x374`. Every installed vptr differs from the proven Participants Manager vptr `0x00ab916c`.

## Rejected sites

- `0x005ded7e`, `FUN_005dec70`: `ESI=ECX`, then `[ESI]=0x00adee38`.
- `0x0074874b`, `FUN_00748280`: `ESI=ECX`, then `[ESI]=0x00b07938`.
- `0x008169c3`, `FUN_008167f0`: `ESI=ECX`, final constructor vptr before the target store is `0x00b16158`.
- `0x00833972`, `FUN_00833760`: `EBX=ECX`, then `[EBX]=0x00b190a8`.
- `0x00844343`, `FUN_00844320`: `ESI=ECX`, then `[ESI]=0x00b190a8`.
- `0x00844b67`, `FUN_00844a20`: `ESI=ECX`, then `[ESI]=0x00b190a8`.
- `0x00d7f104`, `FUN_00d7f040`: `ESI=ECX`, then `[ESI]=0x00ac1fc4`.

The target stores use the same captured receiver. No class-name inference is required: at the physical write point these receivers are objects with vptr identities incompatible with the Participants Manager singleton object.

## Worklist transition

The literal manager-`+0x374` provenance worklist shrinks from **23 sites / 19 functions** to **16 sites / 12 functions**. Computed-address writers remain outside this contract.

The manager `+0x374 -> HDVehicle+0x4330` join remains unproven. Literal `0x004b86cf`, P1.3 completion and provider removal remain fail-closed; provider count remains 7.
