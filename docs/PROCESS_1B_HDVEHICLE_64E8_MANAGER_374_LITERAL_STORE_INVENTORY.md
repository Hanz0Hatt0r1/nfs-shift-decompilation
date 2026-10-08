# Process 1B — Participants Manager `+0x374` literal-store inventory

## Scope

This slice exhaustively inventories retail machine writes whose destination operand is a base register plus the literal displacement `0x374`.

It answers a deliberately narrow question: which machine instructions visibly write `[reg+0x374]`? It does **not** infer that every such register is the Participants Manager root, and it does not cover a writer that first computes `root+0x374` through arithmetic and then writes through another displacement.

PC retail 1.02 `SHIFT.exe` is authoritative. `objdump` is only the decoder. `shift_ghidra.sqlite` supplies containing-function navigation and mnemonic fingerprints.

## Retail inventory

The whole `.text` scan contains exactly **25** literal `+0x374` write sites across **21** containing functions.

Two sites already have exact Participants Manager receiver provenance:

### Constructor zero-init — `0x00488e33`

The singleton initialization path is:

```text
0x00489ae3  mov ecx,0x00bc9fc0
0x00489ae8  call FUN_00488dc0
```

`FUN_00488dc0` then executes:

```text
0x00488dc2  mov esi,ecx
0x00488dca  xor ebx,ebx
...
0x00488e33  mov [esi+0x374],ebx
```

Therefore this writer is exactly:

```text
manager+0x374 = 0
```

It cannot place fixed `HDVehicle+0x4330` into the slot.

### Selection writer — `0x00d606f3`

The already-merged exact-root direct-callee proof establishes `FUN_00d60660` as the sole direct nonzero writer in that surface:

```text
manager+0x374 = selected manager+0x2a0 entry
```

The selected entry belongs to allocator-owned `manager+0x2a0` storage and is not fixed `HDVehicle+0x4330`.

## Remaining worklist

The other **23** literal stores, across **19** functions, remain a receiver-provenance worklist. They are not rejected merely because their displacement is also `0x374`.

The exact sites are pinned in `SHIFT.HDVehicle64e8Manager374LiteralStoreInventory/1`.

## Boundaries

This contract makes `literal_plus_0x374_write_inventory_complete=true`, but keeps all broader gates fail-closed:

- remaining literal-store receiver provenance is incomplete;
- computed-address manager `+0x374` writers are not covered;
- manager `+0x374 == HDVehicle+0x4330` is not proven or disproven globally;
- literal candidate `0x004b86cf` remains open;
- P1.3 remains incomplete;
- external provider count remains 7.

Participants Manager lifecycle writes reached as `(manager+0x20)+0x354` are owned by separate exact-identity contracts and do not need to appear as literal `[manager+0x374]` machine instructions in this inventory.
