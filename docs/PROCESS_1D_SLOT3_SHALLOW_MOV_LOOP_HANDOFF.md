# Process 1D — slot3 shallow custom MOV-loop handoff

## Result

P1D consumes two merged P1A retail-machine closures whose receiver/destination rejections are independent of slot0/slot1 and are also disjoint from selected slot3 `HDVehicle+0x28b8..+0x28bf`.

The consumed contracts are:

- `SHIFT.P1A.P13ASlot01ReceiverLoopMachineClosure/1` — depth<=4 backward loops using an entry-receiver alias, 8 candidates / 8 rejected;
- `SHIFT.P1A.P13ASlot01OrdinaryMovLoopMachineClosure/1` — depth<=4 ordinary-MOV copy/init loops, 5 candidates / 5 rejected.

P1A ownership is not transferred.

## Slot3 application

The exact `HDVehicle` destination domains that survive receiver identity in these bounded scans are:

```text
HDVehicle+0xea..+0xf9
HDVehicle+0x3fe0
HDVehicle+0x407c / +0x3660 / +0x3678
HDVehicle+0x35c8 cursor range
```

None overlaps slot3 target bytes:

```text
HDVehicle+0x28b8 .. HDVehicle+0x28bf
```

All other candidates are exact stack, fixed-global, CRT, allocator/service, or `HDVehicle+0x6730` service-subobject domains. Therefore both bounded shallow loop families are closed negative for slot3.

## Gate

```text
slot3 shallow entry-receiver loop depth<=4       = complete negative
slot3 shallow ordinary MOV copy/init loop <=4     = complete negative
slot3 shallow loop writer found                   = false

straight-line / acyclic unrolled MOV/FST          = open
SSE/custom transforms                             = open
non-entry-alias loops                             = open
deeper direct copy/init                           = open
indirect/callback dispatch                        = open
slot3 writer provenance                           = false
P1.3D complete                                    = false
provider count                                    = 7
```

Reachability and numeric offset coincidence remain navigation evidence only. Exact receiver provenance and target-byte coverage are required for any later promotion.

## Next step

Inventory shallow straight-line unrolled `MOV/FST/SSE` copy/init shapes and loop destinations carried through non-entry aliases. Expand into deeper or indirect paths only when an exact selected-wheel-derived destination survives machine-flow adjudication.
