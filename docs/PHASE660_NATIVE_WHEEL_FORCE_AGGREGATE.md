# Phase 660 — native `FUN_00759c90` wheel-force aggregate

Phase 660 ports the exact three-record reduction recovered in Phase 378 into `shift_runtime_physics`.

## Fixed record geometry

Retail iterates exactly three records beginning at `this + 0x7f0` with `0x150` stride. For each record the native implementation consumes the established fields:

- vector A at relative `+0xb0` multiplied by scalar `+0x00`;
- vector B at relative `+0x98` multiplied by scalar `-0x08`;
- point at relative `+0xf8`.

The two weighted vectors are added. The record point has BODY position `+0x00/+0x08/+0x10` subtracted, and the cross product of that relative point with the summed vector is accumulated.

## Outputs

Across all three records the function returns:

- the sum of the three weighted vectors;
- the sum of the three cross products;
- the weighted-vector sum transformed through the exact native `FUN_007af0a0` float-matrix boundary;
- transformed X divided by the non-zero BODY field at `+0x120`.

The BODY `+0x120` field and record quantities remain semantically unnamed; no mass/force/torque units are assigned.

## Regression

`shift_runtime_wheel_force_aggregate_check` mirrors the established Python oracle:

- three identical records produce total `(9, 6, 0)`;
- the cross accumulator is `(-6, 9, 0)`;
- identity-frame scalar output is `3` for divisor `3`;
- a nontrivial diagonal frame proves reuse of `FUN_007af0a0`;
- zero divisor and non-finite record state fail closed.

## Build organization

Phase 660 introduces `native_runtime/cmake/recent_physics.cmake`. New incremental physics source/check registrations can now use `target_sources()` and focused test declarations without repeatedly replacing the large top-level `native_runtime/CMakeLists.txt`.

`native-physics-recent` is extended to execute the Phase 660 CTest and report alongside Phases 656–659.

## Remaining join

`FUN_00759c90` is a source-backed arithmetic primitive only. Its caller-side scheduling and the larger `FUN_007675f0` surface/distance response kernel remain separate. The latter can now consume a native aggregate without inventing any BODY pose writer or per-frame record producer.
