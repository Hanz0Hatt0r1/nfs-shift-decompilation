# Process 1B — manager `+0x374` receiver rejections

## Scope

The corrected `SHIFT.HDVehicle64e8Manager374LiteralStoreInventory/1` worklist leaves 20 actionable literal `[base+0x374]` stores after inherited negatives. Numeric offset equality is never promoted to identity.

`FUN_00488dc0` pins manager object levels: root singleton `0x00bc9fc0` gets vptr `0x00ab9190`, while embedded manager+0x20 gets vptr `0x00ab916c`.

## Rejected exact receiver families

Six same-body sites use entry receivers explicitly assigned non-root-manager vptrs: `0x0074874b`, `0x008169c3`, `0x00833972`, `0x00844343`, `0x00844b67`, `0x00d7f104`.

Three `FUN_008446a0` sites (`0x008446cb/e3/f8`) are owned by the function's unique whole-PE registration at vtable `0x00b190a8+0x9c`; the function has zero direct callsites and uses its entry `ECX` receiver.

Two sites use the same exact owner+0x56c child constructed by `FUN_008167f0` with final vptr `0x00b16158`. `FUN_0080b8f0` loads exactly `[owner+0x56c]`. This closes `0x00816c9c` directly and `0x00818157` through the `0x00573044` getter path and jump-table methods `FUN_008184e0` / `FUN_008185d0`, both of which preserve the child receiver into `FUN_00818000`.

Two embedded sites (`0x007c0fa0`, `0x007c1ace`) are children of `FUN_007c3170` at `outer+0x8` and `outer+0xfe8`. Its complete direct caller surface is two fresh `0x3848` allocations plus fixed static `0x00c1c568`; neither embedded receiver can be fixed manager singleton `0x00bc9fc0`.

`0x00a44ac5` is an embedded copy receiver. Its only chain is `FUN_008fe2a0` (outer vptr `0x00b35e6c`) -> `outer+0xc` into `FUN_00a451f0` -> `+0x4` into `FUN_00a44a50`, so the target base is exact `outer+0x10`, not manager singleton.

## Boundary

Fourteen newly rejected sites reduce the corrected actionable literal writer worklist from 20 to 6. The six remaining sites are `0x00865013`, `0x0097da09`, `0x0097daf8`, `0x0097dc63`, `0x0097ed06`, and `0x00a38974`. They remain fail-closed pending exact argument/owner provenance. Computed-address writes remain outside this contract.

The manager `+0x374 -> HDVehicle+0x4330` identity join, literal `0x004b86cf`, P1.3 completion, and provider removal remain fail-closed. Provider count remains 7.
