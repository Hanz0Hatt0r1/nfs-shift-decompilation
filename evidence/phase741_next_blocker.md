# Phase 741 next blocker

The selected BMW `FUN_00765c40` pre-query inputs are now narrowed to native-owned world position, persistent `+0x38dc` cache state, and exact selected `+0x38e8` setup fallback.

The remaining residual boundary still owns:

1. collision/world lookup behavior below the typed `FUN_007b0710` query record;
2. the four per-pass wheel `+0x738` load terms returned by `FUN_00765c40`;
3. any remaining source-visible side effects not yet split from the complete pass.

A useful next slice is to identify the collision-provider object/call beneath `FUN_007b0710` and determine whether its lookup can be represented as an earlier typed provider boundary. Do not reduce the provider count until the residual pass can be removed rather than merely renamed.

The same setup value at `HDVehicle+0x38e8` is also read by `FUN_00766510` as an upper clamp bound. Reusing the newly proven selected setup value there is valid only after the current contact-response provider path is inspected and wired explicitly.
