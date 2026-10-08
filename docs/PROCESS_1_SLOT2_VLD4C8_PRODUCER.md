# Process 1 — slot-2 `VehicleLoadData+0x4c8` producer

## BLOCKER

`SHIFT.Fun007530e0Slot2SourceProducer/1` closes the slot-2 source transfer back to `VehicleLoadData+0x3a0/+0x3a8/+0x4c8`, but it intentionally leaves the upstream writers of those fields open.

This slice closes one of the three without assigning control semantics.

## Receiver and selected-HDVehicle call

`FUN_007c3b00` preserves entry `ECX` in `ESI`:

```text
0x007c3b21  ESI = ECX
```

The selected `FUN_0076df50` mode-4 call uses:

```text
0x0076e20a  ECX = [HDVehicle+0x66b4]
0x0076e210  push 4
0x0076e216  push EBX
0x0076e21a  call FUN_007c3b00
```

and `EBX` was established as:

```text
0x0076e1c1  EBX = HDVehicle+0x4330
```

With the exact five-argument stack order, `FUN_007c3b00 [EBP+0x10]` is therefore `HDVehicle+0x4330`; the mode at `[EBP+0x18]` is `4`.

The receiver is the already-proven `VehicleLoadData = *(HDVehicle+0x66b4)`.

## Exact `+0x4c8` transfer

The mode-4 branch executes:

```text
0x007c48ba  EAX = [EDI+0x21b8]
0x007c48c0  compare EAX with -1
0x007c48c8  fild dword [EBP+0x0c]
0x007c48cb  fstp qword [ESI+0x4c8]
```

Because `EDI = HDVehicle+0x4330`, the source normalizes exactly to:

```text
HDVehicle + 0x4330 + 0x21b8 = HDVehicle+0x64e8
```

So when that source is not `-1`:

```text
VehicleLoadData+0x4c8 = f64(int32(HDVehicle+0x64e8))
```

This is an exact PC-retail machine value transfer. It is not a throttle/brake/steering identification.

## Constructor distinction

`FUN_007c3170` constructs the allocated `0x3848`-byte VehicleLoadData object and invokes `FUN_007c0db0` on `VehicleLoadData+0x8`. Those setup/default stores are useful lifecycle evidence but do not replace the selected mode-4 runtime/load transfer above.

## P1.3 state

```text
VehicleLoadData+0x4c8 writer/value transfer = proven
source HDVehicle+0x64e8 writer              = open
VehicleLoadData+0x3a0 writer                = open
VehicleLoadData+0x3a8 writer                = open
retail input/control provenance             = false
P1.3 complete                               = false
provider count                              = 7
```

## NEXT_STEP

Trace the exact writer/value producer of `HDVehicle+0x64e8`, while separately closing `VehicleLoadData+0x3a0/+0x3a8`. Promote a retail control link only after exact value-transfer provenance reaches a genuine input/control producer.
