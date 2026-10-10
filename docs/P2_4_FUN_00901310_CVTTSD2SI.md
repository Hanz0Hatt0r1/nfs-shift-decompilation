# Process 2 P2.4 — `FUN_00901310` CVTTSD2SI value contract

## BLOCKER

`SHIFT.Fun007bf790CasterRecordMaterialization/1` initially retained `FUN_00901310` as an external integer-conversion callback because the rounding rule had not been promoted.

Merged Process 1A machine evidence is stronger than that conservative boundary: `FUN_00901310` spills only the incoming x87 value to a stack qword and converts it to EAX with `CVTTSD2SI`.

## MACHINE AUTHORITY

PC retail `SHIFT.exe` SHA-256:

`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`

Upstream proof: `SHIFT.P1A.P13ASlot01DeeperHDVehicleRootTranche/1`.

The decisive instruction windows are:

```text
0x00901322  DD 1C 24        FSTP qword ptr [ESP]
0x00901325  F2 0F 2C 04 24 CVTTSD2SI EAX,qword ptr [ESP]
```

The upstream proof also establishes that the helper needs no object receiver and has no non-stack destination.

## VALUE SEMANTICS

For the returned EAX value, `CVTTSD2SI` gives a complete deterministic contract:

- source: f64 qword spilled from the incoming x87 value;
- result: signed 32-bit integer;
- rounding: truncate toward zero;
- NaN, infinity or a truncated value outside signed 32-bit range: integer-indefinite `0x80000000`.

The native helper checks the truncated double before the C++ integer cast, so it does not rely on implementation-defined/out-of-range host casts.

## OUTPUT

`SHIFT.Fun00901310Cvttsd2si/1` internalizes the returned EAX value semantics.

`SHIFT.Fun007bf790CasterRecordMaterialization/1` keeps its historical callback overload for instrumentation and compatibility, but now also exposes a no-callback overload that composes this native conversion directly. The caster value path therefore no longer requires an external `FUN_00901310` provider.

The regression covers:

- positive and negative fractional truncation;
- signed zero;
- both signed-32 edge regions;
- NaN/infinity/out-of-range integer-indefinite behavior;
- non-integral caster `Range[2]` and `Setting` values flowing through the native materializer.

## LIMITS

This slice owns the returned integer value, not architectural floating-point status side effects. It does **not** claim MXCSR exception/status-flag parity or floating-point exception delivery.

Caster CDF/VehicleLoadData acquisition remains outside the native owner surface. Therefore `FUN_007584f0_computed_payloads` remains incomplete, no residual-producer promotion bit is set, top-level `FUN_00765c40` remains present, the lower scene query remains external, and external provider count remains **7**.

## NEXT STEP

Bind the source-backed `LeftCasterRange/Setting` and `RightCasterRange/Setting` fields from the existing `SHIFT.VehicleCDFRuntime/1` suspension layout into authoritative native VehicleLoadData/session state. `FUN_00901310` no longer blocks that value path.
