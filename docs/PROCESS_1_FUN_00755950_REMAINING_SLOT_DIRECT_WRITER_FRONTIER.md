# Process 1 — remaining `FUN_00755950` direct-writer frontier

## Result

The direct literal-store search for the three still-open `FUN_00755950` consumer slots is exhausted without promoting any numeric-offset collision as a selected-HDVehicle writer.

Targets remain:

```text
slot 0 -> HDVehicle+0x938
slot 1 -> HDVehicle+0x13b8
slot 3 -> HDVehicle+0x28b8
```

All three now move to alias/callee/bulk-copy provenance.

## Slot 0

Two literal `+0x938` writer families exist.

`FUN_00791020` was already closed by `SHIFT.Fun00791020EmbeddedVehicleOwnership/1`: its receiver is the embedded Vehicle at `actual_participant+0x340`, not selected HDVehicle.

The second candidate is `FUN_007572f0`:

```text
0x007572fe  EDI = entry ECX
0x0075733c  EAX = slot_index * 0xa80
0x00757348  EDI = EAX + entry_ECX + 0x400
...
0x007576b0  fstp f32 [EDI+0x938]
```

Therefore its store normalizes to:

```text
entry_root + 0x400 + slot*0xa80 + 0x938
= entry_root + 0xd38 + slot*0xa80
```

It is not `entry_root+0x938`, so it is rejected as a selected-root slot-0 writer even when a caller proves the entry root itself is HDVehicle.

No direct literal root candidate remains for slot 0.

## Slot 1

The consumer target is qword/f64 `HDVehicle+0x13b8`.

The direct qword literal candidate is:

```text
0x007c4984  fstp qword [ESI+0x13b8]
```

but this occurs in `FUN_007c3b00`, where:

```text
0x007c3b21  ESI = ECX = VehicleLoadData
```

so the store is exactly:

```text
VehicleLoadData+0x13b8
```

not selected `HDVehicle+0x13b8`.

Other literal `+0x13b8` writes in the PE are dword/pointer/object-mismatched candidates and are not promoted to the qword HDVehicle target.

No direct qword root candidate remains for slot 1.

## Slot 3

A full PC-retail PE scan finds no direct literal store to `+0x28b8`. The slot-3 writer therefore cannot be recovered by a direct `[root+0x28b8]` store search and must be reached through alias/callee/bulk-copy provenance.

## Gate

```text
slot-0 direct literal surface exhausted = true
slot-1 direct qword surface exhausted    = true
slot-3 direct literal surface exhausted = true
retail input/control provenance          = false
P1.3 complete                            = false
provider count                           = 7
```

## NEXT_STEP

Search address-taking, subobject-relative, callee and bulk-copy writers for selected `HDVehicle+0x938/+0x13b8/+0x28b8`. Require exact selected-root base provenance and matching write width before promotion. Numeric offset equality alone remains insufficient.
