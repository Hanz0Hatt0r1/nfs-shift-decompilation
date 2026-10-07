# Phase 740 scope

## In scope

- Own the persistent `HDVehicle+0x38dc` query-cache state in `NativeVehicleProviderSession`.
- Preserve the source zero setup seed as `std::nullopt`.
- Pass the current native-owned cache handle into the residual `FUN_00765c40` provider before execution.
- Commit the returned handle before later anchors so pass 1 consumes pass 0 state.
- Preserve the final handle across later explicit steps and retail inner batches.
- Roll the cache state back transactionally on any failed explicit step/batch.
- Require the residual provider to prove it consumed the native-owned cache handle; selected BMW world position remains pre-call owned as established by Phase 739.

## Out of scope

- Collision-provider implementation or ownership under `FUN_007b0710`.
- Physical naming/typing of the returned handle.
- `HDVehicle+0x38e8` miss-fallback setup producer/value.
- Remaining `FUN_00765c40` load-term generation or other side effects.
- Any reduction of the seven top-level external provider boundaries.
- Any substitution of Xbox behavior for PC authority.
