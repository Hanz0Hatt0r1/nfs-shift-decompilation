# Phase 727 scope

Phase 727 is limited to the retail machine-code transform from the stored local query sample to the `FUN_007b0710` world position.

In scope:

- prove the chassis pointer remains `HDVehicle+0x33a0` / selected BMW BODY0;
- prove BODY0 origin `f64` offsets `+0x00/+0x08/+0x10`;
- prove BODY0 basis `f32` offsets `+0xd4..+0xf4`;
- prove local query sample storage `HDVehicle+0x3938/+0x3940/+0x3948`;
- reproduce `FUN_007aefb0` basis multiplication and `FUN_00753590` origin addition natively;
- preserve retail operation/store grouping;
- hash-lock the retail machine spans used for the claim.

Out of scope:

- claiming complete semantics for `FUN_007618f0`, which writes `HDVehicle+0x3938`;
- naming the unresolved local-base/config vector semantics feeding that writer;
- joining the transform to an incorrect outer-step BODY0 snapshot;
- changing the active selected-session `FUN_00765c40` provider API in this phase;
- internalizing the collision provider;
- using renderer BODY0/VHF transforms as wheel-query evidence.

The executable S6 frontier therefore remains the Phase 726 seven-provider frontier until per-pass BODY state and the local-sample producer are joined.
