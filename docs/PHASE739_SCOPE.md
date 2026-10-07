# Phase 739 scope

In scope:

- compose Phase737 current BMW wheel BODY origins with the exact Phase738 selected VehicleLoadData inputs;
- execute the existing Phase728 local-sample arithmetic unchanged;
- execute the existing Phase727 BODY0 basis/origin world transform unchanged;
- publish the result as the selected BMW `Fun00765c40QueryInputBoundary.world_position`;
- reuse the existing pre-anchor `current_body_observer` so pass 1 reads post-half-step persistent BODY state;
- keep generic synthetic lower-chain fixtures distinct from the exact 11-BODY selected BMW domain;
- preserve all remaining `FUN_00765c40` load-term/cache/fallback/collision/side-effect ownership externally.

Out of scope:

- using the renderer/VHF world transform as a substitute for the physics query transform;
- treating a non-BMW BODY array as selected BMW state;
- internalizing collision-provider behavior;
- inventing semantics for cache handle or `+0x38e8` fallback;
- removing the complete `FUN_00765c40` provider before its remaining outputs/side effects are separately owned;
- reducing the active top-level provider count below seven in this phase.
