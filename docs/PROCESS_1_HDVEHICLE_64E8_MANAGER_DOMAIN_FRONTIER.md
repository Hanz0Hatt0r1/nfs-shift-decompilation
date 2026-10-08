# Process 1 — `HDVehicle+0x64e8` manager-domain frontier

## Result

The four literal `+0x21b8` stores from `SHIFT.HDVehicle64e8WriterFrontier/1` collapse into two exact receiver domains rather than four unrelated candidates.

Target normalization remains:

```text
HDVehicle+0x64e8 = (HDVehicle+0x4330) + 0x21b8
```

No candidate is promoted to that target yet.

## Domain A — singleton slot

`0x004b86cf` uses:

```text
0x004b8664  call FUN_00489ad0
0x004b8669  ESI = [EAX+0x374]
...
0x004b86cf  [ESI+0x21b8] = 1
```

The manager constructor at `0x00488dc0` initializes `manager+0x374` to null at `0x00488e33`.

Thus the receiver is exactly the pointer stored in the manager singleton slot `+0x374`.

## Domain B — indexed collection

The other three stores all resolve an object through the same manager collection:

```text
FUN_00489ad0()
  -> manager+0x2a0
  -> FUN_0054ed00(collection, index)
```

and then write:

```text
0x004bb205  receiver+0x21b8 = 4
0x004bca6b  receiver+0x21b8 = 3
0x00d775ee  receiver+0x21b8 = 2
```

This reduces the direct literal candidate problem from four receiver chains to two ownership joins.

## `HDVehicle+0x4330` side

PC retail exposes the selected subobject directly at four important sites:

```text
0x0076b241  ECX = HDVehicle+0x4330 -> FUN_00772200 constructor
0x00768c16  ECX = HDVehicle+0x4330 -> FUN_00772570 update
0x00769551  ECX = HDVehicle+0x4330 -> FUN_00756050 destructor
0x0076e1c1  EBX = HDVehicle+0x4330 -> load/physics forwarding
```

The constructor/update/destructor windows do not directly call `FUN_00489ad0` or `FUN_0054ed00`, and no direct store of the subobject pointer into `manager+0x374` or direct insertion into `manager+0x2a0` is proven there.

That is a **frontier**, not a rejection: registration may happen through an indirect owner path.

## P1.3 state

```text
four literal stores reduced to two receiver domains = true
singleton +0x374 -> HDVehicle+0x4330 join            = open
indexed +0x2a0 -> HDVehicle+0x4330 join              = open
exact HDVehicle+0x64e8 writer                        = false
literal candidates rejected                          = false
retail input/control provenance                      = false
P1.3 complete                                        = false
provider count                                       = 7
```

## NEXT_STEP

Trace the producer/registration paths for `FUN_00489ad0()+0x374` and the `FUN_00489ad0()+0x2a0` collection entries. Promote or reject only after pointer identity is joined to `HDVehicle+0x4330`.
