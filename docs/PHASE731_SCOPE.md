# Phase 731 scope

In scope:

- preserve the existing PC retail `FUN_007675f0 -> FUN_00783a30` arithmetic;
- classify `HDVehicle+0xa0` as the source-owned distance-filter cap;
- use the Xbox 360 retail build only as an independent ownership cross-check;
- remove `distance_filter_cap` from production `ContactOuterSessionInput`;
- expose an explicit one-time `Fun007675f0DistanceFilterCapSetup` seed;
- preserve compatibility-only seeding for historical fixtures;
- keep the active top-level external-provider count at seven.

Out of scope:

- the upstream initializer or selected BMW value for `HDVehicle+0xa0`;
- physical naming or units for the cap;
- changes to `FUN_00783a30` math;
- closing the remaining six `FUN_007675f0` caller inputs;
- reducing the complete `FUN_00765c40`, wheel-update, contact-response, scalar-provider, half-step-refresh, or post-half-step boundaries without separate source-backed proof.
