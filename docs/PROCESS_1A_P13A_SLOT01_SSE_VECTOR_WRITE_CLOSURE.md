# Process 1A / P1.3A — shallow SSE/vector write closure

After shallow ordinary-MOV and x87 zero/copy-init classes were closed, SSE/MMX stores remained as the last direct-depth<=4 machine-write class that could move or zero vector data without an ordinary scalar store.

The hash-locked analyzer follows direct calls from the four P1.3A roots to depth four, maps them through the Drive Ghidra SQLite index, and disassembles the authoritative PC retail 1.02 executable. It records explicit XMM/MM-to-memory stores, separately inventories implicit `MASKMOVQ/MASKMOVDQU` stores, and also follows XMM/MM-to-GPR extraction (`movd`, `pextrw`, `pmovmskb`, `movmsk*`) until clobber/call to catch an ordinary non-stack store of extracted bits.

## Retail result

The bounded direct-call graph has 377 reachable nodes, of which 371 have sized Ghidra function ranges. Exactly 14 explicit vector-to-memory stores exist in this surface, across four functions:

- `FUN_009011e0`: 3 stores;
- `FUN_00909e0e`: 2 stores;
- `FUN_0090a37e`: 3 stores;
- `FUN_00911e19`: 6 stores.

All 14 destinations are `ESP` stack slots (`[esp+0x4]` or `[esp+0x10]`). There are zero direct non-stack vector stores, zero implicit `MASKMOVQ/MASKMOVDQU` stores, and zero vector-to-GPR non-stack memory stores before the extracted carrier is clobbered or crosses a call boundary.

Therefore the complete shallow direct-depth<=4 SSE/MMX write surface contains no selected-HDVehicle writer for slot0 `+0x938` or slot1 `+0x13b8`.

## Gate

```text
shallow SSE/vector depth<=4 surface complete = true
direct vector memory stores                  = 14
stack-only direct stores                     = 14
non-stack direct stores                      = 0
implicit MASKMOVQ/MASKMOVDQU stores          = 0
vector->GPR non-stack escapes                = 0
selected slot0/slot1 writer found            = false
deeper direct aliases ruled out              = false
indirect/callback aliases ruled out           = false
slot0 complete                               = false
slot1 complete                               = false
P1.3 complete                                = false
provider count                               = 7
```

Next: stop broadening instruction classes at shallow depth and trace only deeper direct or indirect/callback paths that carry an exact selected-HDVehicle-derived destination alias.
