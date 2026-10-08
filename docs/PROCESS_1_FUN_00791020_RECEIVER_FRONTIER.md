# Process 1 — `FUN_00791020` receiver frontier

## Result

The next P1.3 machine writer candidate can now be bounded by its receiver flow.

`FUN_00791020` writes `f32` values at `receiver+0x938` on two control branches (`0x007910f8` and `0x0079113e`). That numeric offset matches the slot-0 HDVehicle-root offset consumed by the already-proven `FUN_00755950` boundary, but numeric equality alone is not object identity.

## Proven setup path

Retail machine code contains a direct setup path:

```text
0x0074e2b6  ECX = [ESI]
0x0074e2b8  ECX += 0x340
0x0074e2be  call FUN_00799ff0
```

`FUN_00799ff0` immediately preserves that receiver and calls the candidate writer:

```text
0x00799ff1  ESI = ECX
0x00799ff3  call FUN_00791020
```

Therefore this path proves:

```text
FUN_00791020.this = *(setup_context) + 0x340
```

It does **not** prove:

```text
*(setup_context) + 0x340 == selected HDVehicle
```

The identity of the object loaded at `0x0074e2b6` remains open.

## Second direct call

The other direct machine call is:

```text
0x00799f76  ECX = ESI
0x00799f7e  call FUN_00791020
```

This confirms another same-receiver-style invocation inside the surrounding update family, but the enclosing object has not yet been joined to selected HDVehicle either.

## Join to the wheel consumer

`SHIFT.Fun00755950AbsoluteConsumedFieldMachineProof/1` proves that wheel slot 0 consumes:

```text
HDVehicle + 0x938
```

`FUN_00791020` writes:

```text
receiver + 0x938
```

The offset match is useful navigation evidence only. Until `receiver == selected HDVehicle` is proven, `FUN_00791020` cannot be promoted as the upstream writer for the wheel-consumed field.

## P1.3 gate

```text
FUN_00791020 setup receiver flow proven       = true
receiver is *(setup_context)+0x340             = true
+0x340 child == selected HDVehicle             = false
FUN_00791020 is wheel-field writer             = false
retail input/control provenance                = false
P1.3 complete                                  = false
external provider count                        = 7
```

No throttle, brake, steering, suspension, or other physical semantic label is assigned.

## NEXT_STEP

Trace the pointer loaded at `0x0074e2b6` backward to its owner/lifecycle evidence and prove or reject whether its `+0x340` child is the selected HDVehicle. Only after that receiver join should the `FUN_00791020 +0x938` stored value be traced backward.
