# Process 1B — Participants Manager `+0x374` literal-store inventory

## Scope

This slice exhaustively inventories retail machine writes whose destination operand is a base register plus the literal displacement `0x374`.

It answers a deliberately narrow question: which machine instructions visibly write `[reg+0x374]`? It does **not** infer that every such register is the Participants Manager root, and it does not cover a writer that first computes `root+0x374` through arithmetic and then writes through another displacement.

PC retail 1.02 `SHIFT.exe` is authoritative. `objdump` is only the decoder. `shift_ghidra.sqlite` supplies containing-function navigation and mnemonic fingerprints.

## Retail inventory

The whole `.text` scan contains exactly **25** literal `+0x374` write sites across **21** containing functions.

Two sites have exact Participants Manager receiver provenance:

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

Therefore this writer is exactly `manager+0x374 = 0`. It cannot place fixed `HDVehicle+0x4330` into the slot.

### Selection writer — `0x00d606f3`

The merged exact-root direct-callee proof establishes:

```text
manager+0x374 = selected manager+0x2a0 entry
```

The selected entry belongs to allocator-owned `manager+0x2a0` storage and is not fixed `HDVehicle+0x4330`.

## Inherited negative sites

Three additional literal sites are already closed by merged receiver-provenance contracts and are not reopened by this inventory:

- `0x004826a6` / `FUN_00481e20`: all direct destination surfaces are closed as stack-local, SMS participant `+0xa00` render snapshot, or `CCameraView+0x2d0` state;
- `0x0051effd` / `FUN_0051efa0`: exact receiver `0x00be1680`, distinct from manager singleton `0x00bc9fc0`;
- `0x005ded7e` / `FUN_005dec70`: fresh `0x37c` allocation is too small for the Participants Manager layout, whose constructor writes through `+0x37f`.

These facts come from `SHIFT.HDVehicle64e8Manager374LiteralWriterRejections/1`, `SHIFT.HDVehicle64e8Manager374BulkCopyParticipantRejection/1`, and `SHIFT.HDVehicle64e8Manager374BulkCopyCameraRejection/1`.

## Remaining worklist

After preserving those merged negatives, **20** literal stores across **16** functions remain a receiver-provenance worklist. They are not rejected merely because their displacement is also `0x374`.

The exact ordered sites and containing-function fingerprints are pinned in `SHIFT.HDVehicle64e8Manager374LiteralStoreInventory/1`.

## Boundaries

This contract makes `literal_plus_0x374_write_inventory_complete=true`, but keeps all broader gates fail-closed:

- remaining literal-store receiver provenance is incomplete;
- computed-address manager `+0x374` writers are not covered;
- manager `+0x374 == HDVehicle+0x4330` is not proven or disproven globally;
- literal candidate `0x004b86cf` remains open;
- P1.3 remains incomplete;
- external provider count remains 7.

Participants Manager lifecycle writes reached as `(manager+0x20)+0x354` are owned by separate exact-identity contracts and do not need to appear as literal `[manager+0x374]` machine instructions in this inventory.
