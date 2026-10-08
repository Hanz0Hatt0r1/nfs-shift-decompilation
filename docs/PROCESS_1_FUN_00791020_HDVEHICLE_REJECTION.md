# Process 1 — reject `FUN_00791020` as selected-HDVehicle `+0x938` writer

## Result

`FUN_00791020` writes `receiver+0x938`, but its receiver is not the selected `HDVehicle` root.

PC-retail machine code proves:

```text
FUN_00715240
  element = [manager+0x140] + queue_index*0x1fa0
  call FUN_007125e0(element)
  call FUN_0074e1a0(element) at 0x007152f3

FUN_007125e0
  allocates 0x2b90 bytes
  constructs the returned object with FUN_0072ed20
  stores it at [element+0] at 0x0071263e

FUN_0074e1a0
  setup_context = [element+0]
  receiver = setup_context+0x340
  call FUN_00799ff0 at 0x0074e2be

FUN_00799ff0
  preserves that receiver and calls FUN_00791020
```

Thus the candidate write belongs to the `+0x340` child of a freshly allocated `0x2b90` object.

Existing selected-HDVehicle proof independently establishes `HDVehicle+0x66b4`. A root object whose proven layout reaches `+0x66b4` cannot be the freshly allocated `0x2b90` setup object. Therefore the matching `+0x938` literal is not a same-root ownership join.

No semantic class name is assigned to the `0x2b90` object or its child. This result only rejects selected-HDVehicle root identity.

## Gate

```text
FUN_00791020 receiver provenance resolved = true
FUN_00791020 selected-HDVehicle root       = false
FUN_00791020 actual HDVehicle+0x938 writer = false
retail control provenance                  = false
P1.3 complete                              = false
provider count                             = 7
```

## NEXT_STEP

Continue the absolute writer search for `HDVehicle+0x938/+0x13b8/+0x1e38/+0x28b8`. Accept a candidate only after its receiver/base is independently joined to selected `HDVehicle`; raw numeric offset matches remain navigation evidence only.
