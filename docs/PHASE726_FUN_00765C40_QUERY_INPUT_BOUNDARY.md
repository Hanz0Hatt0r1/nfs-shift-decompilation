# Phase 726 — source-backed FUN_00765c40 collision-query input boundary

## Result

Phase 726 narrows the still-external complete `FUN_00765c40` pass without inventing the transform that produces its collision-query position.

Existing PC retail evidence already proves the immediate caller-visible boundary before `FUN_007b0710`:

- three finite world-position values `(x, y, z)`;
- previous query/cache handle propagated to query-record `+0x30`;
- caller state `+0x38e8`, reused as the miss fallback;
- the query builder adds exactly `+0.15` to `y`, sets `+0x18 = 200.35`, `+0x20 = 9.999999933815813e36`, and uses cache-aware `param_3 = 1`;
- after a hit, caller scalar `+0x38e0` is `original_world_y - contact_height`; on a miss it is `+0x38e8`.

`Fun00765c40QueryInputBoundary` now represents exactly those source-backed inputs. It can materialize the already-native `CollisionQueryRecord` and project the already-proven hit/miss scalar through the Phase 666 contract.

## Active session handoff

`Fun00765c40ExternalPassResult` is advanced to `SHIFT.Fun00765c40ExternalPassResult/2` and now contains:

- the already-proven `Fun00765c40LoadTerms`;
- the `Fun00765c40QueryInputBoundary` consumed by that external pass.

`NativeVehicleProviderSession` validates and snapshots that query input once for each of the two recovered `FUN_0076d100` passes. The snapshots are exposed in `NativeVehicleProviderSessionResult`, so the exact external input no longer disappears behind an opaque complete-pass callback.

## What remains external

Phase 726 does **not** prove or internalize the producer of `(x,y,z)`. Existing Phase 370/665/666 evidence explicitly leaves that transform external. The already-closed BODY0/VHF renderer world-transform chain is not substituted for it.

Likewise, Phase 726 does not implement the track/surface collision provider below `FUN_007b0710` / `FUN_0074f560`. It only reuses the already-native source-backed query-record and observable hit/miss contracts.

The active external-provider count therefore remains seven.

## Next proof target

Trace the source dataflow that produces the three position values consumed at the `FUN_00765c40 -> FUN_007b0710` call site. In parallel, recover collision-provider ownership beneath `FUN_007b0710` without assigning unsupported PhysX class names or substituting renderer transforms.
