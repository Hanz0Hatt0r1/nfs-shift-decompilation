# Phase 409 — unified SDF full-frame contract

The reconstructed SDF physics path is now represented as one lifecycle contract spanning the frame entry, per-body matrix construction, scalar solve and post-solve body application.

## Exact lifecycle

`FUN_007b3f40` enters the frame. `FUN_007b3ed0` refreshes constraint-side state, `FUN_007bb8d0` resets each body's solver contribution storage, `FUN_007bc680` builds JOINT/HINGE/BAR contributions, and `FUN_007ba570` exports per-body vector/matrix contributions to the global solver buffers. `FUN_007b2210` applies identity row/column resets for runtime constraint samples whose `+0x70` low bit is set. The solver then dispatches to provider virtual slot `+0x18` or builtin `FUN_007b0f20`. Finally `FUN_007b4110` applies solved scalars back to body state.

## Static vs runtime readiness

All storage, coupling, seed and lifecycle functions are source-backed and statically complete. Identity-reset selection is runtime-dependent because the selector bit is read from live runtime sample `+0x70`; without those flags the selector is explicitly reported as not-ready rather than inferred from scalar index parity.

The unified frame runtime exposes this distinction so later captured frames can inject the actual selector words and receive exact scalar-node reset lists. It does not claim that provider-owned vtable implementations are reconstructed.
