# Phase 728 — exact FUN_007618f0 producer for HDVehicle+0x3938

## Result

Phase 728 recovers the exact machine-code formula that writes the local collision-query sample consumed by Phase 727.

The PC retail writer is inside `FUN_007618f0`. Without assigning unsupported suspension/vehicle semantic names to its inputs, the dataflow is exact:

- load an `f64 vec3` through the pointer at `HDVehicle+0x820`;
- load an `f64 vec3` through the pointer at `HDVehicle+0x12a0`;
- add the vectors through `FUN_00753590` and store the `f64` sum;
- multiply that stored vector by the exact `f64` constant `0.5` through `FUN_007535f0` and store the midpoint;
- form a local base where X/Z come from the midpoint while Y is replaced with the negated `f64` value from the second source argument `+0x338`;
- add the inline `f64 vec3` at the second source argument `+0x918` through `FUN_00753590`;
- store the final vector to `HDVehicle+0x3938/+0x3940/+0x3948`.

In formula form:

`midpoint = 0.5 * (vec(*HDVehicle+0x820) + vec(*HDVehicle+0x12a0))`

`local_base = { midpoint.x, -source[0x338], midpoint.z }`

`HDVehicle.local_sample_0x3938 = local_base + source.vec3[0x918]`

The midpoint Y component is computed by the retail helper but is not used in `local_base`.

## Native implementation

`execute_fun_007618f0_local_sample_producer()` reproduces those stages with explicit `f64` store boundaries between vector addition, the 0.5 multiply, Y replacement and the final vector addition.

The native regression also composes the produced local sample with Phase 727's exact BODY0 transform to verify the recovered source cores form a coherent chain.

## Remaining ownership work

Phase 728 does not claim semantic identities or lifetimes for:

- the pointer stored at `HDVehicle+0x820`;
- the pointer stored at `HDVehicle+0x12a0`;
- the second `FUN_007618f0` source argument containing `+0x338` and `+0x918`.

Those storage-owner joins remain external. The selected-session runtime also still needs the correct current BODY0 snapshot at each `FUN_00765c40` pass before Phase 727 can replace the external world-position value.

The active external-provider count remains seven.
