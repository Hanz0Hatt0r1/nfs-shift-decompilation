# Process 1 — `FUN_00755950` absolute consumed-field proof

## Result

The PC-retail machine code closes an offset-normalization ambiguity in P1.3.

`FUN_00758b50` calls `FUN_00755950` once per selected wheel slot with:

```text
this = HDVehicle + 0x400 + slot*0xA80
slot = 0..3
```

At `0x00755956`, `FUN_00755950` copies `ECX` to `EDX`. At `0x00755958` it reads:

```text
f64 [EDX + 0x538]
```

Therefore the actual HDVehicle-root fields consumed by this helper are:

```text
slot 0: HDVehicle + 0x938
slot 1: HDVehicle + 0x13B8
slot 2: HDVehicle + 0x1E38
slot 3: HDVehicle + 0x28B8
```

The loaded value is then reduced by the explicit `relative_length` argument before the helper chain continues. No physical name is assigned to the value.

## Rejected false writer candidate

A machine scan also finds `FUN_007618f0` writing literal `[ESI+0x538]` at `0x00761b67`. Existing PC-retail ownership proof already establishes its receiver as `HDVehicle`.

Inside that function:

```text
0x00761933  ESI = HDVehicle + 0x748
...
0x00761b67  store f64 [ESI + 0x538]
...
0x00761ce2  ESI += 0xA80
```

So those writes normalize to:

```text
HDVehicle + 0xC80
HDVehicle + 0x1700
HDVehicle + 0x2180
HDVehicle + 0x2C00
```

They are not the `FUN_00755950` consumed fields. The identical literal `+0x538` occurs relative to two different proven bases. Treating literal offset equality as same-field identity would therefore be incorrect by exactly `0x348` bytes.

## Remaining candidate

Retail machine code contains writes to `receiver+0x938` in `FUN_00791020` at:

```text
0x007910f8
0x0079113e
```

Two direct machine callsites are visible at `0x00799f7e` and `0x00799ff3`, both forwarding their current receiver in `ECX`.

This is only a writer candidate. The current proof does not establish that the `FUN_00791020` receiver is the selected retail HDVehicle object. That receiver/base join is the next exact question.

## P1.3 gate

```text
FUN_00755950 absolute consumed slots proven = true
FUN_007618f0 +0x538 writer rejected         = true
exact upstream writer owner proven          = false
retail input/control provenance proven       = false
P1.3 complete                                = false
external provider count                      = 7
```

No throttle, brake, steering, suspension, or force semantics are inferred from these offsets.

## NEXT_STEP

Resolve the `FUN_00791020` receiver at its two direct retail machine callsites. If it aliases the selected HDVehicle, trace the stored `receiver+0x938` value backward and establish the corresponding four-slot writer topology. Otherwise reject it and continue the absolute-offset writer search.
