# Phase 407 — retail identity-row/column reset

`FUN_007b2210` is now modeled at the same storage level as the reconstructed SDF matrix. When the provider pointer at physics-system `+0x48` is null, the builtin path zeroes the selected scalar row, zeroes the selected scalar column, writes `1.0` at the diagonal and zeroes the matching RHS entry. The source performs these operations in that order.

The new runtime helper applies the operation through the actual row-index array and flat matrix pool used by the retail layout (`+0x3c/+0x38` globally, `+0x158/+0x154` per body, with `+0x15c` row-index offsets). `build_solver_ready_matrix()` now returns both the logical matrix and a retail-compatible storage view.

The provider branch remains explicit: when a solver provider exists, `FUN_007b2210` dispatches to virtual slot `+0x1c` instead of executing the builtin row/column loops.

This phase closes the source-faithful matrix-initialization path. It does not imply that the provider implementation is reconstructed; that remains a separate boundary.
