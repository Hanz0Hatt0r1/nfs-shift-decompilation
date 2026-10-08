# Process 1 — slot-2 VehicleLoadData `WedgeRange` runtime writer

## Result

The post-construction writer owner for the two VehicleLoadData fields feeding the proven slot-2 source chain is now closed.

PC retail loads the literal resource key:

```text
WedgeRange
```

into three `double` destinations whose first two normalize exactly to:

```text
VehicleLoadData+0x3a0
VehicleLoadData+0x3a8
```

This proves the runtime/load writer path. It does not yet prove the selected numeric resource values or any throttle/brake/steering meaning.

## Owner chain

`FUN_007c3b00` receives the already-proven `VehicleLoadData` object in `ECX`:

```text
0x007c3b21  ESI = ECX = VehicleLoadData
```

Later it invokes the loader helper with:

```text
0x007c4009  ECX = ESI+0x8 = VehicleLoadData+0x8
0x007c400c  call FUN_007be420
```

`FUN_007be420` preserves that nested receiver:

```text
0x007be43f  ESI = ECX = VehicleLoadData+0x8
```

## `WedgeRange` destinations

The exact call setup is:

```text
0x007be8ab  push 0
0x007be8ad  ECX = nested+0x3a8 ; push ECX
0x007be8b4  EDX = nested+0x3a0 ; push EDX
0x007be8bb  EAX = nested+0x398 ; push EAX
0x007be8c2  push 0x00b0ec24   ; "WedgeRange"
0x007be8c7  ECX = parser/loader receiver
0x007be8c9  call FUN_007a6a90
```

Because the nested base is `VehicleLoadData+0x8`, the three destinations are:

```text
nested+0x398 = VehicleLoadData+0x3a0
nested+0x3a0 = VehicleLoadData+0x3a8
nested+0x3a8 = VehicleLoadData+0x3b0
```

## Parser boundary

`FUN_007a6a90` first resolves the supplied key through `FUN_007a6320`. On this three-destination branch, it forwards the source buffer and destination pointers to `FUN_00901423` with the exact retail format literal:

```text
(%lf,%lf,%lf)
```

Thus all three destinations are runtime/load `double` outputs of the `WedgeRange` entry.

The backend/source-buffer internals are not promoted beyond this machine-proven boundary, and the selected BMW numeric values are not claimed here.

## Join to slot-2

Existing `SHIFT.Fun007530e0Slot2SourceProducer/1` proves:

```text
VehicleLoadData+0x3a0 -> HDVehicle+0x5238
VehicleLoadData+0x3a8 -> HDVehicle+0x5240
```

Therefore their post-construction writer owner is now closed to the `WedgeRange` resource-load path.

## P1.3 state

```text
VLD+0x3a0 bootstrap value              = proven 0.0
VLD+0x3a8 bootstrap value              = proven 0.0
VLD+0x3a0 post-construction writer     = proven WedgeRange load
VLD+0x3a8 post-construction writer     = proven WedgeRange load
selected loaded numeric values         = open
HDVehicle+0x64e8 non-sentinel writer   = open
retail input/control provenance        = false
P1.3 complete                          = false
provider count                         = 7
```

## NEXT_STEP

Continue the first non-sentinel selected `HDVehicle+0x64e8` writer. Trace the selected `WedgeRange` resource values only if that numeric provenance becomes necessary; do not infer control-axis semantics from the key name or field positions.
