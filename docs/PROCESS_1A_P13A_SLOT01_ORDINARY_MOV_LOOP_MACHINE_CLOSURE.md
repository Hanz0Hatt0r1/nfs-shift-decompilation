# Process 1A / P1.3A — shallow ordinary MOV loop closure

## Scope

After the REP and canonical bare MOVS/STOS subsets closed, slot0 `HDVehicle+0x938` and slot1 `HDVehicle+0x13b8` still had an ordinary `MOV` copy/init class where a compiler loop advances a non-stack destination without calling a named memory routine.

`analyze_p1a_slot01_ordinary_mov_loop_frontier.py` bounds that class to direct-call depth four from the four recovered wheel/physics roots. A candidate must contain a backward branch plus an ordinary `MOV` memory-transfer or zero-init store whose destination-address register changes inside the loop. The detector is clobber-aware: a memory load transformed by `LEA`/arithmetic before a later store is not treated as a copy carrier.

## Retail result

The pinned PC retail 1.02 image and Drive Ghidra SQLite index yield exactly five candidate functions. All five reject as selected slot0/slot1 writers:

- `FUN_00765c40`: the loop destination starts at receiver `+0x35c8`, not `+0x938/+0x13b8`.
- `FUN_00764266`: `EDI=EBP-0xd0`; the loop is stack-local zero initialization.
- `FUN_00a62940`: `FUN_00765c40` passes receiver `+0x6730`; the loop maintains `+0x44`, stride-`0x30` service records and their nodes.
- `FUN_0090db22`: the path enters via `FID_conflict:_wprintf`; its recovered signature is a CRT formatter over `FILE*`/buffer/locale/wchar inputs.
- `FUN_00a62fd0`: called with the same `+0x6730` service receiver; its loop compacts `+0x44 + index*0x30` record slots.

A superficially copy-like pointer-table loop in `FUN_007bb8d0` is intentionally absent: the loaded value is transformed by `LEA` before the store, so it does not satisfy the ordinary memory-copy carrier definition.

## Gate

```text
shallow ordinary MOV copy/init depth<=4 complete = true
candidate functions                            = 5
rejected candidates                            = 5
selected slot0/slot1 writer found              = false
straight-line unrolled MOV complete             = false
deeper direct paths ruled out                  = false
indirect/callback copy dispatch ruled out       = false
slot0 complete                                 = false
slot1 complete                                 = false
P1.3 complete                                  = false
provider count                                 = 7
```

## Next step

Inventory straight-line unrolled ordinary-MOV copy/init sequences in the same shallow frontier. Only after that should P1A expand deeper or indirect paths, and only when exact selected-HDVehicle destination provenance is carried.
