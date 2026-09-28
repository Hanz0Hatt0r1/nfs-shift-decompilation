# Phase 423 — builtin sparse solver restoration

The repository contained `tests/test_sdf_builtin_sparse_solver_runtime.py` and the source-backed `FUN_007b0f20` execution contract, but the corresponding runtime module was missing. Phase 423 restores it.

## Runtime model

The restored module exposes the expected `n+1` forward / `n` reverse graph shape and an executable symmetric LDL-style numerical reference. Lower-triangle entries hold normalized factors, while the diagonal stores the factorization pivots. The upper triangle mirrors those factors so source-visible relations such as `A[i][j] = A[j][i] / A[i][i]` remain inspectable.

The reference implements forward substitution, diagonal solve and backward substitution and is covered by deterministic 3×3 and 4×4 regression systems, including a zero-pivot guard.

This module is a reconstruction/reference implementation of the builtin path; provider-specific solver behavior remains separate.
