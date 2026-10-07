# Phase 726 next blocker

Phase 726 exposes the exact source-backed input consumed by the `FUN_00765c40 -> FUN_007b0710` query boundary and preserves it for both recovered physics passes. Query-record materialization and hit/miss scalar projection are native; the producer of the three position values and the collision provider remain external.

## NEXT_STEP

Recover the source dataflow that produces `(x,y,z)` at the `FUN_00765c40` query call site (PC decompiler source line 759173) and identify the ownership/refresh boundary of the previous cache handle.

The proof must determine the actual coordinate producer rather than borrowing the renderer BODY0/VHF transform. If the full transform still cannot be proven, narrow the upstream producer to the smallest source-backed vector/matrix/input contract.

Separately, continue tracing ownership below `FUN_007b0710` / `FUN_0074f560` toward the track/surface collision provider. Do not assign PhysX class names or collision semantics that are not source-backed.

Preserve all already-native/closed boundaries:

- `FUN_00758ad0` arithmetic and its storage topology;
- `FUN_007b0710` query-record and observable hit/miss contract;
- native wheel query/response join;
- typed `Fun00765c40LoadTerms` ownership;
- Phase 724 `FUN_007682c0` closure;
- selected-session retail scheduler and BODY0/VHF renderer transform.

Until the producer/provider ownership is proven, keep complete `FUN_00765c40` external and the active provider count at seven.
