# Phase 740 review checklist

- [x] PC retail remains authoritative.
- [x] `HDVehicle+0x38dc` is treated only as opaque caller-owned cache state.
- [x] Source zero setup seed maps to `std::nullopt`.
- [x] Residual `FUN_00765c40` receives the current cache before execution.
- [x] Returned handle is committed before later pass anchors.
- [x] Pass 1 consumes pass 0 returned state.
- [x] Cache persists across explicit steps/retail batches.
- [x] Cache rolls back on failed work.
- [x] Selected BMW world position is also supplied pre-call rather than overwritten after provider execution.
- [x] Collision-provider implementation remains external.
- [x] `+0x38e8` fallback remains unresolved for the next phase.
- [x] Top-level external provider count remains seven.
