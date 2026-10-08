# Process 1 — `HDVehicle+0x64e8` bootstrap sentinel

## Result

The first exact writer of the selected `HDVehicle+0x64e8` field is now proven through an alias/callee path in the constructor. Fresh state is:

```text
HDVehicle+0x64e8 = int32 -1
```

This closes bootstrap value provenance only. It does not identify the later writer that changes the field to another value.

## Alias/callee writer

The selected HDVehicle path constructs the embedded record directly:

```text
0x0076b241  ECX = HDVehicle+0x4330
0x0076b247  call FUN_00772200
```

Inside `FUN_00772200`:

```text
0x007722d4  EDI = record+0x21a4
0x007722e0  call FUN_00458a80   ; ECX = EDI
```

`FUN_00458a80` initializes a contiguous block:

```text
0x00458a80  EDX = ECX
0x00458a84  EAX = 0xffffffff
0x00458a87  EDI = receiver+0x4
0x0045b5df  ECX = 0x3e
0x00458a8f  rep stos dword [EDI], EAX
```

Sixty-two dwords are therefore set to `0xffffffff`, covering `receiver+0x4` through `receiver+0xf8` inclusive.

The target is exactly inside that range:

```text
record+0x21b8
= (record+0x21a4)+0x14
```

Therefore fresh selected state is exactly `-1`.

## Consumer sentinel behavior

The mode-4 `FUN_007c3b00` path does:

```text
0x007c48ba  EAX = [record+0x21b8]
0x007c48c0  compare EAX with -1
0x007c48c6  if equal -> jump 0x007c48d1
0x007c48c8  otherwise convert int32
0x007c48cb  otherwise store f64 VehicleLoadData+0x4c8
```

Thus fresh constructor state deliberately suppresses the `VehicleLoadData+0x4c8` overwrite.

## Relation to the manager-domain frontier

`SHIFT.HDVehicle64e8ManagerDomainFrontier/1` found literal stores of `1`, `2`, `3`, and `4` at the same numeric record offset. Those remain plausible later writers, but none is promoted until its receiver is joined to the selected `HDVehicle+0x4330` record.

## P1.3 state

```text
bootstrap alias/callee writer             = proven
fresh HDVehicle+0x64e8 value              = -1
fresh mode-4 VLD+0x4c8 overwrite          = skipped
first post-construction non--1 writer     = open
retail input/control provenance           = false
P1.3 complete                             = false
provider count                            = 7
```

## NEXT_STEP

Trace the first post-construction writer that changes the selected `HDVehicle+0x64e8` away from `-1`. Continue the manager `+0x374` / `+0x2a0` joins only with exact pointer/index ownership; otherwise enumerate other alias/callee writes.
