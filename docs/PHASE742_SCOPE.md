# Phase 742 scope

In scope:

- advance the active residual result to `SHIFT.Fun00765c40ExternalPassResult/4`;
- expose typed `CollisionQueryOutput` on the selected BMW path;
- validate that the output belongs to the exact source-backed query input;
- validate hit/miss/contact-height/cache-output consistency;
- bind the source-visible returned cache write to `CollisionQueryOutput.returned_handle`;
- preserve generic historical fixtures that do not represent the selected 11-BODY BMW domain;
- provide a native helper for the `FUN_00765c40` `+0x38e0` projection and first `FUN_00766510` `[0,+0x38e8]` clamp;
- refresh the current provider frontier through Phase742 while leaving the Phase699 inventory immutable.

Out of scope:

- executing the collision/world lookup provider natively;
- assigning undocumented physical semantics to the collision result or caller scalar;
- wiring the new scalar handoff through `NativeVehicleProviderSession` in this phase;
- removing the `FUN_00766510` contact-response provider;
- internalizing primary response BODY application or the `+0x40a0/+0x40a8/+0x40b0` accumulator;
- internalizing additional conditional branches inside `FUN_00766510`;
- reducing the seven-provider frontier.
