# Phase 486 — BODY solver-domain matrix builder

## Goal

Phase 486 closes the structural gap left by Phase 485. The existing BODY matrix routine already proved the local rule used by `FUN_007ba2b0`; this phase supplies its missing input: ordered runtime constraint scalar blocks from the `FUN_007b1b60` solver domain.

## Construction

For every ordered runtime constraint record:

1. take its recovered solver width (`JOINT=3`, `HINGE=2`, `BAR=1`);
2. take its ordered scalar block (`scalar_base .. scalar_base+width`);
3. attach that block to every BODY referenced by `posbody` or `negbody`;
4. for each BODY, apply the Phase 485 Cartesian-product rule across all local groups;
5. write structural `1.0` symmetrically for every generated matrix cell.

This reproduces the data-flow boundary:

`FUN_007b1b60 ordering → FUN_007b3820 scalar blocks → FUN_007b2010 → FUN_007ba2b0 → pre-acceptance matrix`

## Outputs

The builder returns:

- BODY-local width/scalar groups;
- per-BODY cell sets;
- the full structural 0/1 matrix;
- total and strict-upper non-zero counts;
- diagonal coverage and symmetry checks.

`compare_structure_to_seed()` can compare this generated support with a captured or previously extracted seed matrix without comparing numeric coefficients.

`evaluate_generated_acceptance()` runs the existing source-backed provider sparsity predicates on the generated matrix. This reports a candidate match only; it does not infer provider identity.

## BMW guard

`build_bmw_matrix_structure()` requires the already established BMW shape of 11 BODY records, 28 runtime constraint records and 40 scalar nodes. It refuses other dimensions instead of silently labeling them as BMW.

## Important boundary

The builder depends on an already ordered solver domain. It does not independently reproduce the `FUN_007b1b60` ordering heuristic or decode the SDF resource itself; those responsibilities remain in the existing solver-domain and SDF layers.

The generated matrix is a structural seed. It does not reconstruct the later dynamic coefficient accumulation, nor does it prove a provider class identity.
