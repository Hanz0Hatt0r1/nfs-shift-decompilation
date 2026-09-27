# Phase 402 — End-to-end SDF matrix assembly

All three retail matrix-writing kernels are now represented together: `FUN_007bbb80` for JOINT-centric blocks, `FUN_007bb250` for HINGE/HINGE and HINGE/BAR, and `FUN_007bb6c0` for BAR/BAR.

## Source-faithful storage

The assembler operates only on lower-triangle writes addressed through the `+0x158` row-pointer table. It does not synthesize upper-triangle entries and does not apply the later `FUN_007b2210` identity resets.

## Recovered block set

The combined set is: JOINT self 3×3, JOINT/JOINT 3×3, JOINT/HINGE 3×2, JOINT/BAR 3×1, HINGE self 2×2 lower triangle, HINGE/HINGE 2×2, HINGE/BAR 2×1 or 1×2, and BAR/BAR 1×1.

`materialize_symmetric_view()` is deliberately a separate derived operation for analysis and tests.

This phase closes the coefficient matrix topology at the builtin solver boundary. Remaining work is to validate the assembled matrix against captured runtime values and to integrate solved-vector application with full body-state updates.
