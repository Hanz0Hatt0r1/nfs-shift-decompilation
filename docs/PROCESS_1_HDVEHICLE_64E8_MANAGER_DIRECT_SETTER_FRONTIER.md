# Process 1 — `HDVehicle+0x64e8` manager direct-setter frontier

## Result

The singleton-side ownership question from `SHIFT.HDVehicle64e8ManagerDomainFrontier/1` is narrower now.

The candidate path is still:

```text
FUN_00489ad0() -> manager
manager+0x374 -> candidate receiver
candidate receiver+0x21b8 -> literal store at 0x004b86cf
```

To make that store the selected target, the pointer in `manager+0x374` must be proven identical to `HDVehicle+0x4330`.

A full-retail direct-call receiver inventory found 44 calls, across 12 unique targets, where `ECX` at the callee is still the unmodified pointer returned by `FUN_00489ad0`. None of those 12 direct callee bodies contains a direct store to receiver `+0x374`.

The constructor remains the only proven direct slot writer in this bounded surface:

```text
0x00488e33  [manager+0x374] = 0
```

This does **not** prove the slot remains null. Indirect calls, virtual dispatch, helper-mediated writes, pointer aliases, and bulk-copy/registration paths remain open.

## Direct receiver target inventory

```text
FUN_004042e0  19 calls
FUN_00489430   5 calls
FUN_00489480   5 calls
FUN_00489310   4 calls
FUN_00402400   2 calls
FUN_004892c0   2 calls
FUN_00487240   2 calls
FUN_004894d0   1 call
FUN_00488a60   1 call
FUN_00488ad0   1 call
FUN_0048c070   1 call
FUN_004939e0   1 call
```

Calls where the getter result is adjusted before dispatch, for example calls on `manager+0x20`, are deliberately excluded because they are not direct manager-root receivers.

## Gate

```text
constructor zero of manager+0x374                   = proven
direct manager-root receiver setter to +0x374      = not found
direct manager-root receiver setter surface        = exhausted
indirect / virtual / alias setter                   = open
manager+0x374 == HDVehicle+0x4330                   = open
exact HDVehicle+0x64e8 non-sentinel writer          = false
retail input/control provenance                     = false
P1.3 complete                                       = false
external provider count                             = 7
```

No gameplay meaning is assigned to `manager+0x374`, `receiver+0x21b8`, or `HDVehicle+0x64e8`.

## NEXT_STEP

Trace indirect/virtual/helper mutations of `manager+0x374`. In parallel, trace insertion producers for the second manager domain (`manager+0x2a0`). Only promote the literal `+0x21b8` stores after exact pointer identity reaches `HDVehicle+0x4330`.
