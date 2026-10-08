# Process 1 — reject `FUN_00791020` as the selected-HDVehicle `+0x938` writer

## Result

`FUN_00791020` writes `receiver+0x938`, but its setup-path receiver is not the selected `HDVehicle` root.

The machine chain is:

```text
FUN_00715240
  array_base = [manager+0x140]
  element = array_base + queue_index*0x1fa0
  call FUN_007125e0(element)
  call FUN_0074e1a0(element) at 0x007152f3

FUN_007125e0
  allocates 0x2b90 bytes
  constructs the returned object with FUN_0072ed20
  stores the allocated pointer at [element+0] at 0x0071263e

FUN_0074e1a0
  setup_context = [element+0]
  receiver = setup_context+0x340
  call FUN_00799ff0 at 0x0074e2be

FUN_00799ff0
  preserves ECX as receiver
  calls FUN_00791020
```

Therefore the `FUN_00791020` `receiver+0x938` writes belong to a `+0x340` child of a freshly allocated `0x2b90` object.

## Why this is not the selected HDVehicle root

Existing PC-retail ownership proof already establishes a selected-HDVehicle field at `HDVehicle+0x66b4` (`SHIFT.Fun007618f0VehicleLoadDataOwnership/1`). A root object with a proven field at `+0x66b4` cannot be the freshly allocated `0x2b90` setup object.

The numerical `+0x938` coincidence is therefore rejected as a same-root writer join.

This does **not** assign a semantic class to the `0x2b90` object and does not claim that it is unrelated to vehicle simulation. The only promoted conclusion is that it is not the selected `HDVehicle` root whose absolute `+0x938/+0x13b8/+0x1e38/+0x28b8` fields are consumed by the `FUN_00758b50 -> FUN_00755950` path.

## Gate

```text
FUN_00791020 receiver provenance resolved = true
FUN_00791020 selected-HDVehicle root       = false
FUN_00791020 actual +0x938 wheel writer    = false
retail control provenance                  = false
P1.3 complete                              = false
provider count                             = 7
```

## NEXT_STEP

Continue the absolute writer search for `HDVehicle+0x938/+0x13b8/+0x1e38/+0x28b8`, accepting only stores whose receiver/base is independently joined to selected `HDVehicle`. Do not reuse raw `+0x938` offset matches across unrelated allocated objects.
