# Phase 744 scope

In scope:

- advance the active residual result to `SHIFT.Fun00765c40ExternalPassResult/4`;
- expose typed `CollisionQueryOutput` on the selected BMW path;
- validate that the output belongs to the exact source-backed query input;
- validate hit/miss/contact-height/cache-output consistency;
- bind the source-visible returned-cache write to `CollisionQueryOutput.returned_handle`;
- preserve generic historical fixtures that do not represent the selected 11-BODY BMW domain;
- provide a native helper for the `FUN_00765c40` `+0x38e0` projection and first `FUN_00766510` `[0,+0x38e8]` clamp;
- preserve Phase742 primary response BODY application and Phase743 selected application-point ownership as separate closed sub-boundaries.

Out of scope:

- executing the collision/world lookup provider natively;
- assigning undocumented physical semantics to the collision result or caller scalar;
- wiring the new scalar handoff through `NativeVehicleProviderSession` in this phase;
- removing the `FUN_00766510` contact-response provider;
- deriving the remaining `+0x3908/+0x3910/+0x3918/+0x3950` response configuration;
- internalizing caller configuration, diagnostic accumulation, auxiliary scheduling or other conditional branches inside `FUN_00766510`;
- reducing the seven-provider frontier.
