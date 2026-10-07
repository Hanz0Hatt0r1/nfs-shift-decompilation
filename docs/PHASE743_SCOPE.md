# Phase 743 scope

In scope:

- prove `HDVehicle+0x38f0/+0x38f8/+0x3900` is written by the Phase727 BODY0-basis transform inside `FUN_00765c40`;
- prove the same stored vec3 is read later by `FUN_00766510` as the point argument of the Phase742 `FUN_007baa70` application;
- reuse the Phase684 same-pass anchor order;
- alias the point to `Fun00765c40WorldPositionTransformResult.body_rotated_local`;
- explicitly distinguish this scratch point from the origin-added collision `world_position`.

Out of scope:

- changing the `contact_response` provider API;
- passing the owned point into the residual callback at runtime;
- removing the `contact_response` provider;
- deriving remaining `FUN_00766510` response configuration fields;
- reducing the active top-level provider count below seven.
