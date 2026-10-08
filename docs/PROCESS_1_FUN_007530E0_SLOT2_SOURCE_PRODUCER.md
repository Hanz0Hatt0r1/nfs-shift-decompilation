# Process 1 — slot-2 source producer

## Result

The three HDVehicle source fields feeding the proven `FUN_007530e0` slot-2 writer are populated through one exact PC-retail transfer chain from the already-owned VehicleLoadData object.

```text
VehicleLoadData+0x3a0 -> HDVehicle+0x5238
VehicleLoadData+0x3a8 -> HDVehicle+0x5240
VehicleLoadData+0x4c8 -> FUN_00901310 -> HDVehicle+0x524c
```

No control semantics or physical units are assigned.

## Owner/call chain

`FUN_0076df50` keeps HDVehicle in `ESI`, builds `HDVehicle+0x4330`, and invokes `FUN_007c3b00` with receiver `*(HDVehicle+0x66b4)` (the independently proven VehicleLoadData object) and arg3 `HDVehicle+0x4330`.

Inside `FUN_007c3b00`:

```text
0x007c3b1e EDI = arg3 = HDVehicle+0x4330
0x007c3b21 ESI = ECX = VehicleLoadData
...
0x007c50ae push EDI
0x007c50af ECX = VehicleLoadData+0x8
0x007c50b2 call FUN_007bfbe0
```

Inside `FUN_007bfbe0`:

```text
0x007bfbff ESI = arg1 = HDVehicle+0x4330
0x007bfc06 EDI = ECX = VehicleLoadData+0x8
...
source pointer = EDI+0x398 = VehicleLoadData+0x3a0
destination    = ESI+0xf08 = HDVehicle+0x5238
qword arg      = EDI+0x4c0 = VehicleLoadData+0x4c8
0x007bfd56 call FUN_007c5a20
```

## Exact transfer

`FUN_007c5a20` copies the first two qwords and converts the third input through `FUN_00901310`:

```text
HDVehicle+0x5238 = qword VehicleLoadData+0x3a0
HDVehicle+0x5240 = qword VehicleLoadData+0x3a8
HDVehicle+0x524c = EAX returned by FUN_00901310(x87 qword VehicleLoadData+0x4c8)
```

`FUN_00901310` contains environment-dependent conversion branches, so this proof deliberately preserves it as a machine conversion boundary rather than assigning a stronger rounding semantic.

## Join to slot-2 writer

The merged `SHIFT.Fun007530e0Slot2WriterMachineProof/1` uses:

```text
x = f64(HDVehicle+0x5238)
  + f64(int32(HDVehicle+0x524c)) * f64(HDVehicle+0x5240)
```

Therefore the source triplet owner/value transfer is now closed back to VehicleLoadData fields `+0x3a0/+0x3a8/+0x4c8`.

## P1.3 gate

```text
slot-2 source field producer chain      = true
HDVehicle destination identity          = true
VehicleLoadData source identity         = true
source value transfer                   = true
VehicleLoadData upstream field writers = false
retail input/control provenance         = false
P1.3 complete                           = false
provider count                          = 7
```

## NEXT_STEP

Trace the PC-retail writers/value producers of `VehicleLoadData+0x3a0`, `VehicleLoadData+0x3a8`, and `VehicleLoadData+0x4c8`. Do not promote them to throttle/brake/steering or another control meaning without an exact value-transfer proof.
