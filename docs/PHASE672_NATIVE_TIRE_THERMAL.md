# Phase 672 — native `FUN_00760b50` tyre thermal arithmetic

Phase 672 ports the already source-backed Phase 362 per-wheel thermal update into `shift_runtime_physics` as `SHIFT.NativeTireThermal/1`.

The phase deliberately stops at the standalone arithmetic/state-write boundary. It does not schedule the function inside `NativeRuntimeState`, does not invent the transform that produces the longitudinal component, and does not assign physical units to the recovered fields.

## Source-backed boundary

The existing reference oracle is `src/physics/tire_thermal_runtime.py`, backed by `evidence/tire_thermal_source_evidence.json`. The recovered function is `FUN_00760b50` at source line 756009 and is called once per wheel by `FUN_00770e80` after the main physics passes.

The native API preserves the recovered per-wheel `0xA80` stride and the known field offsets, including `+0x350`, `+0x858`, `+0x868`, `+0x870`, `+0x878`, `+0x888`, `+0x890`, `+0x898`, `+0x8A0`, `+0x8A8`, `+0x8B0`, `+0x8B8`, `+0x8C0`, and `+0x8C8`.

## Ordered arithmetic

`execute_fun_00760b50_thermal_step()` preserves the source/reference order:

1. `source_heat = abs(spin_measure) * spin_heat_scale`, then multiply by the accumulated heat scale;
2. retain only the magnitude of a negative supplied longitudinal component;
3. add the `273.16` Kelvin bias to the two ambient inputs and average them;
4. build the affine speed-transfer term and multiply it by the ambient/temperature difference;
5. add source heat to obtain the net heat term;
6. if reserve is at or below the floor, divide by the floor;
7. otherwise compute the cubic depletion term in source order, apply the external overheat scale and `dt`, and update reserve;
8. if the depleted reserve remains at or above the floor, divide by that reserve and update the failure-gain field using the exact tolerance/random branch;
9. otherwise zero reserve and failure gain and force the rate to zero;
10. update the temperature state by `rate * dt`.

All arithmetic exposed by the existing Phase 362 Python oracle is retained as `double`. Phase 672 introduces no additional float32 narrowing and makes no stronger storage-width claim than the source/oracle evidence currently supports.

## Persistent-write mask

The native result distinguishes arithmetic values from source-visible writes:

- the low-reserve floor-normalization path leaves the reserve and failure-gain fields untouched;
- the high-reserve path writes the depleted reserve;
- the successful high-reserve path also writes the tolerance/randomly scaled failure gain;
- the exhausted-reserve path writes zero to both fields;
- the temperature state is always represented by `temperature_after`.

This prevents the earlier Python helper's convenience return value from being misread as proof of a low-reserve `+0x868` write.

## External producers deliberately retained

Two inputs remain explicit precomputed values:

- the longitudinal component after the source-visible wheel/vector transform;
- the overheat scale produced by `FUN_00749340(&DAT_00c12c90) * DAT_00c12f38`.

The failure RNG is also supplied as a pre-sampled scalar so this arithmetic kernel does not invent a random-number provider or call timing.

## Fail-closed behavior

The native boundary rejects:

- non-finite input state;
- zero divisors on an actually selected normalization path;
- non-finite intermediate products/sums;
- overflow to non-finite reserve, rate, failure-gain, or temperature output.

These checks are native admission policy and are not claimed to be retail exception behavior.

## Regression and CI

`shift_runtime_tire_thermal_check` covers:

- the Phase 362 low-reserve floor-normalization fixture;
- source heat, negative-longitudinal magnitude, ambient Kelvin average and convective/net heat terms;
- high-reserve cubic depletion;
- both tolerance branches of the failure-gain update;
- reserve exhaustion with zero reserve/rate/failure gain;
- the source-visible write mask;
- zero-divisor, non-finite-input and overflow rejection.

The target is registered through `native_runtime/cmake/recent_physics.cmake`, and `native-physics-recent` is extended through Phase 672.

## Remaining boundary

Phase 672 does not claim the two-pass `FUN_00770e80` scheduler, does not wire thermal updates into the fixed-step runtime, and does not implement the unresolved transform producer for the longitudinal component. The next safe scheduler step remains dependent on a sufficiently proven `FUN_0076d100`/half-step ordering boundary rather than an inferred retail frame schedule.
