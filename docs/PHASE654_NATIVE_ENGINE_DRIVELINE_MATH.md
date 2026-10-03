# Phase 654 — native engine/driveline math boundary

Phase 653 closes the provider-absent BODY constraint-solver state loop across
native fixed steps. The next playable-vehicle dependency is the source-backed
engine/driveline path that can eventually turn admitted control state into
wheel/body contributions. Phase 654 ports the arithmetic pieces that are
already proven without guessing the still-unresolved control wiring.

The native contract is:

```text
SHIFT.NativeVehicleDrivelineMath/1
```

implemented by:

- `native_runtime/include/shift_vehicle_driveline_math.hpp`;
- `native_runtime/src/vehicle_driveline_math.cpp`;
- `native_runtime/tests/vehicle_driveline_math_check.cpp`.

## `FUN_007becb0` RPMTorque sampling

The recovered EDF loader stores each textual `RPMTorque=(rpm, brake, throttle)`
record as the three source-backed channels:

```text
+0x00 brake
+0x08 throttle
+0x10 rpm
record stride 0x20
```

`sample_fun_007becb0_rpm_torque()` reproduces the already recovered runtime
sampling behavior:

1. choose the first/last segment for out-of-range RPM or the bracketing segment
   for an in-range RPM;
2. linearly interpolate/extrapolate both torque channels with the same scalar;
3. when the sampled brake channel exceeds the sampled throttle channel, replace
   both with their midpoint.

No input-pedal mapping is introduced. The names `brake` and `throttle` here are
the source-backed EDF tuple/channel labels already proven by the loader; this
phase does not claim how a gameplay throttle command selects or blends those
channels.

The native helper also ports the recovered post-load peak scan:

```text
rpm * throttle * 0.73756105 / 5252.0
```

with the same initial peak value `1.0`.

## `FUN_007af310` dense linear solve

`FUN_007af310` is shared by at least two already recovered vehicle paths:

- dimension 4 while building tire/response cubic coefficients;
- dimension 6 from `FUN_00764266` while integrating the driveline.

The native implementation preserves the recovered algorithmic contract:

- search the current/lower rows for a non-zero pivot;
- swap rows when required;
- normalize the pivot row;
- eliminate the pivot column from every other row;
- report failure when no non-zero pivot exists.

The API intentionally exposes the result as anonymous solution lanes. Phase 360
proved five post-solve sign/threshold checks, but the physical identities of the
six `FUN_00764266` variables remain unresolved and are not named here.

## Regression

`shift_runtime_vehicle_driveline_math_check` covers:

- in-range RPMTorque interpolation;
- low/high segment extrapolation;
- the midpoint-clamp branch;
- the recovered peak-power scan;
- a numeric 2x2 solve;
- explicit pivot-row swap;
- dimension-4 and dimension-6 solve paths;
- singular-system failure;
- fail-closed non-monotonic RPM input.

The code is compiled into `shift_runtime_physics` and registered as
`shift_runtime_vehicle_driveline_math` in CTest.

## Remaining boundary

Phase 654 deliberately does **not** connect `VehicleControlIntent::throttle` to
an RPMTorque channel and does not construct the six-equation `FUN_00764266`
driveline system. Those require the exact runtime control/state writers and
coefficient assembly from the recovered HDV path.

Likewise, this phase does not solve the separate BODY position/orientation
motion bridge. It only removes two arithmetic gaps that would otherwise block a
source-backed drivetrain implementation once those state joins are recovered.
