# Process 1 — slot-2 `VehicleLoadData+0x4c8` `WedgeSetting` base writer

## Result

The slot-2 `VehicleLoadData+0x4c8` field has a machine-proven resource-load writer before the already-known optional mode-4 override.

PC retail loads the exact resource key:

```text
WedgeSetting
```

as one `double` directly into:

```text
VehicleLoadData+0x4c8
```

The selected numeric value is not claimed here.

## Owner chain

`FUN_007c3b00` receives the owned VehicleLoadData object:

```text
0x007c3b21  ESI = ECX = VehicleLoadData
```

and invokes:

```text
0x007c4009  ECX = VehicleLoadData+0x8
0x007c400c  call FUN_007be420
```

Inside `FUN_007be420`, `ESI` is that nested receiver.

## Exact `WedgeSetting` destination

```text
0x007be8ce  push 0
0x007be8d0  push 0
0x007be8d2  push 0
0x007be8d4  ECX = nested+0x4c0
0x007be8da  push ECX
0x007be8db  push 0x00b0ec14   ; "WedgeSetting"
0x007be8e0  ECX = parser/loader receiver
0x007be8e2  call FUN_007a6a90
```

Receiver normalization gives:

```text
(VehicleLoadData+0x8)+0x4c0 = VehicleLoadData+0x4c8
```

## Parser boundary

For this argument shape `FUN_007a6a90` takes its single-destination path and calls the parser backend using the exact format literal at `0x00b0c570`:

```text
(%lf)
```

The success path checks for one assignment. Therefore `VehicleLoadData+0x4c8` is a resource-loaded `double` destination of `WedgeSetting`.

## Relation to the mode-4 override

Merged `SHIFT.Fun007530e0Slot2VehicleLoadData4c8Producer/1` proves a later optional mode-4 transfer:

```text
if HDVehicle+0x64e8 != -1:
    VehicleLoadData+0x4c8 = f64(int32(HDVehicle+0x64e8))
```

Merged `SHIFT.HDVehicle64e8BootstrapSentinel/1` proves fresh:

```text
HDVehicle+0x64e8 = -1
```

so the fresh mode-4 path skips that override and preserves the preceding `WedgeSetting` load.

This does not prove that the field remains `-1` for all runtime updates.

## P1.3 state

```text
VLD+0x4c8 resource base writer          = proven WedgeSetting
fresh mode-4 override                   = skipped by -1 sentinel
runtime non-sentinel override           = open
selected WedgeSetting numeric value     = open
retail input/control provenance         = false
P1.3 complete                           = false
provider count                          = 7
```

## NEXT_STEP

Determine whether selected `HDVehicle+0x64e8` ever leaves `-1` before the relevant slot-2 transfer. If no positive writer is joined, the effective source remains the `WedgeSetting` resource value. Do not infer control-axis semantics from the key name.
