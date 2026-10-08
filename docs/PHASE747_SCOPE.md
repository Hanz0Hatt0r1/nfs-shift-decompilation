# Phase 747 scope

In scope:

- reuse the existing PC-retail owner proof for `HDVehicle+0x3fe8`;
- prove the `FUN_00766510` shared reference source is three f32 lanes at actual participant `+0x16b4/+0x16b8/+0x16bc`;
- prove `FUN_00713630` is the dynamic writer of those lanes;
- preserve the source-visible `FUN_007144a0` update condition;
- reproduce the explicit per-lane f32-to-f64 widening and existing `FUN_007af0a0` BODY-frame transform;
- narrow the remaining contact-response ownership blocker without changing the seven-provider frontier.

Out of scope:

- assigning physical names or units to the participant source vector;
- freezing the vector as selected-session setup data;
- reconstructing the upstream dynamic X/Z generator inputs;
- scheduling the early `+0x3b20` branch or auxiliary pair in the selected session;
- internalizing the optional `+0x3bc8/+0x3cxx` branch;
- removing `contact_response` or reducing the provider count.
