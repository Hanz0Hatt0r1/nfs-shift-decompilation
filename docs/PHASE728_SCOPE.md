# Phase 728 scope

Phase 728 is limited to the exact-offset retail source core that produces `HDVehicle+0x3938/+0x3940/+0x3948`.

In scope:

- preserve the pointer-backed `f64 vec3` inputs at `HDVehicle+0x820` and `HDVehicle+0x12a0` as exact-offset inputs;
- preserve the second source argument's `f64 +0x338` scalar and inline `f64 vec3 +0x918` as exact-offset inputs;
- preserve the `FUN_00753590` f64 vector-add store boundary;
- preserve the `FUN_007535f0` exact `0.5` f64 scale/store boundary;
- replace midpoint Y with `-source_scalar_0338` before the final add;
- emit the final local sample consumed by Phase 727.

Out of scope:

- naming the semantic role of the two HDVehicle pointer targets;
- proving their allocation/lifetime/refresh ownership;
- assigning a semantic class to the second source argument;
- wiring the source core into the selected-session external provider;
- solving the per-pass BODY0 timing join;
- internalizing the collision provider.

The executable S6 frontier remains at seven external providers until those owner/timing joins are source-backed.
