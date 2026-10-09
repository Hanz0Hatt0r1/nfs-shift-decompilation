# Process 1A / P1.3A — wheel `+0x538..+0x53f` overlap-store closure

## Blocker

Slot0 `HDVehicle+0x938` and slot1 `HDVehicle+0x13b8` are consumed as f64/qword values through wheel-local `+0x538`. Previous work closed the exact qword store and literal `+0x538` address-forwarding subset, but a full f64 can also be built by two DWORD stores and a high-DWORD-only write at `+0x53c` can still mutate the value.

The direct literal store surface therefore has to be defined by **byte-range overlap**, not by matching one mnemonic or one exact displacement.

## Whole-image machine inventory

`inventory_p1a_slot01_overlap_stores.py` scans hash-locked PC retail `SHIFT.exe` with function ownership from the pinned Ghidra SQLite and records every supported direct memory store whose literal destination range overlaps local bytes `[0x538,0x540)`.

The result is exact for this machine-instruction class:

```text
sized Ghidra functions scanned : 41,538
overlapping store instructions : 25
functions owning them          : 13
unowned instructions           : 0
partial-width stores           : 24
qword-or-wider stores          : 1
```

The only qword store is the already-closed `0x00761b67 fstp qword [esi+0x538]` in `FUN_007618f0`; its proven base is `HDVehicle+0x748+slot*0xa80`, normalizing to `HDVehicle+0xc80/+0x1700/+0x2180/+0x2c00`, never slot0 or slot1.

The remaining 24 stores are owned by 12 functions. Every receiver is rejected from the selected wheel-root domain.

## Reused receiver closures

Existing machine contracts already close nine receiver families:

- `FUN_00481e20`: all direct destinations are stack-local, SMS participant `+0xa00` render snapshot, or `CCameraView+0x2d0` state.
- `FUN_004876f0`: exact nested receivers `outer+0x110` / `outer+0xa00`; its `+0x538/+0x53c` stores normalize to `outer+0x648/+0x64c` or `outer+0xf38/+0xf3c`.
- `FUN_004dbdb0`: separately allocated `0x600` object.
- `FUN_0051f4b0`: fixed singleton `0x00be1680`; four sites write only the high DWORD `+0x53c`.
- `FUN_00748280`: fixed PhysicsTweaker `0x00c12c40`.
- `FUN_007a1fc0`: separately allocated TBC compound array, stride `0x610`.
- `FUN_007a25d0`: configuration-table object, not the iterated wheel receiver.
- `FUN_007c0db0`: `VehicleLoadData+0x8` subobject of a separately allocated `0x3848` object.
- `FUN_007618f0`: the already-closed wrong-base qword store described above.

## New receiver closures

### `FUN_005cb010`

`FUN_005c1150` allocates array nodes with exact stride `0x560` and installs vptr `0x00adc8c0`. Vtable slot 2 (`0x00adc8c8`) is `0x005d1ba0`. That copy method materializes `node+0x8` at `0x005d1ba1` and the sole direct call to `FUN_005cb010` is `0x005d1bba` with that receiver. There are no literal function-pointer occurrences for `FUN_005cb010`.

Thus its stores at `subobject+0x538/+0x53c` normalize to separately allocated node `+0x540/+0x544`, not selected HDVehicle wheel bytes.

### `FUN_00860bf0`, `FUN_008614c0`, `FUN_008620b0`

`FUN_008323d0` allocates exactly `0x8c0` bytes at `0x0083281e..0x00832829`, then constructs the result with `FUN_00860bf0` at `0x00832837`. The constructor installs vptr `0x00b1dae0` at `0x00860c15`.

Vtable slot 0 is `FUN_00862b40`. That method keeps the same receiver and calls `FUN_008620b0` at `0x00862b51` or `FUN_008614c0` at `0x00862b79`. The teardown path also reinstalls `0x00b1dae0` before cleanup.

Therefore the `+0x538/+0x53c` stores in all three functions belong to the separate `0x8c0` object, not the embedded HDVehicle wheel runtime.

## Gate

```text
exact literal overlap-store surface complete = true
selected slot0/slot1 literal writer found    = false
computed-address store surface complete       = false
escaped-alias surface complete                = false
bulk-copy/init surface complete               = false
slot0 complete                                = false
slot1 complete                                = false
P1.3 complete                                 = false
provider count                                = 7
```

## Next step

Drop the exact-literal direct-store class from the frontier. Continue only with computed destinations, escaped aliases, inline/custom bulk-copy or initialization ranges, and indirect dispatch, requiring exact selected-HDVehicle root provenance before any slot completion gate changes.
