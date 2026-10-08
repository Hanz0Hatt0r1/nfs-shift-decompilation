# Process 1 — `HDVehicle+0x64e8` writer frontier

## BLOCKER

The slot-2 chain now reaches one exact upstream root field:

```text
HDVehicle+0x64e8
  -> selected mode-4 transfer
  -> VehicleLoadData+0x4c8
  -> FUN_00901310
  -> HDVehicle+0x524c
  -> FUN_007530e0
  -> HDVehicle+0x1e38
  -> FUN_00755950
```

The remaining question is the writer/value producer of `HDVehicle+0x64e8`.

## Absolute-to-subobject normalization

The source is inside the already-owned `HDVehicle+0x4330` object:

```text
0x4330 + 0x21b8 = 0x64e8
```

Known direct receiver paths include constructor `FUN_00772200(HDVehicle+0x4330)` and update `FUN_00772570(HDVehicle+0x4330)`. PC-retail disassembly shows neither function contains a direct literal store to receiver `+0x21b8`.

That excludes them only as **direct literal writers**; it does not exclude writes through callees or aliases.

## Bounded literal writer surface

A full PE disassembly scan finds four literal memory-write instructions targeting `+0x21b8`:

```text
0x004b86cf  dword [ESI+0x21b8] = EBX
0x004bb205  dword [ESI+0x21b8] = 4
0x004bca6b  dword [ESI+0x21b8] = 3
0x00d775ee  dword [EAX+0x21b8] = 2
```

No candidate is promoted to the target yet. Each receiver/base must first be proven to alias the exact `HDVehicle+0x4330` subobject.

The first candidate is especially bounded: around `0x004b86cf`, `ESI` is loaded through the global-manager path `call 0x00489ad0 -> [EAX+0x374]`. That is navigation evidence only; equality with the selected HDVehicle subobject is not assumed.

## Gate

```text
full literal +0x21b8 writer set bounded = true
constructor direct writer               = false
update direct writer                    = false
exact HDVehicle+0x64e8 writer           = false
alias/callee writer surface exhausted   = false
retail input/control provenance          = false
P1.3 complete                            = false
provider count                           = 7
```

## NEXT_STEP

Resolve receiver provenance for the four literal stores, starting with `0x004b86cf`. Accept a candidate only after an exact PC-retail receiver/base join to `HDVehicle+0x4330`; otherwise reject it and continue through the finite list. If all four are rejected, move to alias/callee-side-effect writer tracing rather than inventing a producer.
