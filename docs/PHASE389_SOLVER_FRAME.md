# Phase 389 — Per-frame SDF solver lifecycle

NaNcontribution accumulation, scalar row fixing, final solve dispatch and post-solve body-state application.

## Frame order

The retail order is:

1. Clear the global solver matrix and RHS when no provider is installed; otherwise call provider vtable `+0x20`.
2. Run `FUN_007b3ed0` to refresh constraint-side sampled state.
3. For every body, run `FUN_007bb8d0`, then `FUN_007bc680`, then `FUN_007ba570` to accumulate its solver-vector/matrix contributions into the global buffers.
4. Apply `FUN_007b2210` to scalar rows selected by the runtime constraint low-bit flag.
5. Dispatch the solve to provider vtable `+0x18` or builtin `FUN_007b0f20`.
6. After the solve, run `FUN_007b4110` to consume the solved scalar vector and update runtime body state.

## Storage

The global scalar solver count is at `+0x34`, row-pointer array at `+0x3c`, RHS vector at `+0x40`, provider pointer at `+0x48`, and the solver object/state pointer used by the builtin call at `+0x4c`.

Per-body `+0x150` is a solver-vector contribution buffer; `+0x154` is a flat solver-matrix contribution buffer; `+0x158` is the matrix row-pointer table and `+0x15c` is its row-index vector.

## Post-solve application

`FUN_007b4110` reads solved values from global `+0x40`. JOINT consumes three consecutive scalar entries, HINGE two, and BAR one. JOINT/BAR call the positive/negative body accumulator primitives `FUN_007baa70`/`FUN_007baaf0`; HINGE updates positive and negative body angular channels directly from its two solved scalars and the sampled rows.

The implementation keeps the body accumulator channels as raw storage coordinates and does not assign unsupported physical units.

## Provider boundary

Provider implementations at vtable `+0x20`, `+0x1c` and `+0x18` remain opaque. The builtin path is source-backed down to the sparse solver traversal reconstructed in Phase 387.
