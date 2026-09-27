# Phase 406 — exact SDF scalar seed writes

`FUN_007ba2b0` is now represented separately from the numeric JOINT/HINGE/BAR coefficient kernels. Its source-visible operation is to seed the solver matrix with `1.0` across the Cartesian product of every runtime constraint's scalar block and every compatible shared-body block, writing both symmetric cross-products.

The new runtime module enumerates those concrete `(row,column,value=1.0)` writes, materializes the normalized seed matrix, and computes a deterministic byte hash. This is intentionally a connectivity/initialization layer: it does not assign physical meaning to the ones, and the later `FUN_007b2210` identity-row resets remain separate.

For the real BMW M3 `aarm_multilink.sdf`, the reconstructed 28-record / 40-scalar domain yields a 40×40 seed matrix with 700 non-zero cells (43.75% density) before identity-row resets. This gives a concrete target for future captured-runtime matrix comparisons even before numeric coefficient reconstruction is complete.
