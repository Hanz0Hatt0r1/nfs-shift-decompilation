# Process 1 — `FUN_00791020` embedded Vehicle ownership

## Result

The unresolved receiver from `SHIFT.Fun00791020ReceiverFrontier/1` is now joined to an existing PC-retail object-lifetime proof.

`SHIFT.BMWOffset33bActualAdditionalMassBootstrapZero/1` already proves:

```text
FUN_007125e0(manager_record)
  -> allocate 0x2b90 bytes
  -> FUN_0072ed20(actual PhysicsParticipant)
  -> manager_record[0] = actual_participant
  -> actual_participant+0x340 = embedded Vehicle
```

The `FUN_00791020` setup path is the same manager-record path:

```text
FUN_00715240
  -> element = manager-record array entry
  -> FUN_007125e0(element)
  -> FUN_0074e1a0(element)
       setup_context = [element+0] = actual_participant
       receiver = setup_context+0x340 = embedded Vehicle
       -> FUN_00799ff0
            -> FUN_00791020
```

Therefore the two machine stores at `0x007910f8` and `0x0079113e` are proven writes to:

```text
embedded Vehicle+0x938
```

They are not writes to `HDVehicle+0x938`.

## P1.3 effect

This closes the object identity of the candidate without promoting it into the selected-HDVehicle wheel-state lane:

```text
FUN_00791020 embedded Vehicle receiver = proven
Vehicle+0x938 writer                    = proven
HDVehicle+0x938 writer                  = false
retail control provenance               = false
P1.3 complete                           = false
provider count                          = 7
```

No new semantic meaning is assigned to `Vehicle+0x938`; this contract is ownership only.

## NEXT_STEP

Continue the selected-HDVehicle writer search for `+0x938/+0x13b8/+0x1e38/+0x28b8` independently. Keep `FUN_00791020` on the embedded-Vehicle lane and do not reintroduce it as an HDVehicle candidate from offset equality alone.
