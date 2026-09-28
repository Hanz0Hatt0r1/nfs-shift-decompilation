# Phase 432 — BMW M3 provider compatibility gate

Phase 432 compares the fixed specialized-provider signatures from Phase 431
with the real BMW M3 E36 seed evidence already committed in
evidence/bmw_m3_e36_sdf_seed_phase406.json.

## Result

The BMW seed has 40 solver scalars, 700 non-zero cells in the full 40x40
matrix, symmetry and a unit diagonal. Therefore its strict upper triangle
contains (700 - 40) / 2 = 330 non-zero cells.

Provider 0 also has a 40-scalar dimension, but its fixed acceptance signature
requires 450 non-zero strict-upper cells. Therefore provider 0 cannot accept
the BMW seed sparsity mask as-is; 120 additional strict-upper cells would have
to become non-zero during numeric matrix population.

Provider 1 expects dimension 34, so it is dimension-incompatible with the BMW
40-scalar domain before sparsity is considered.

## Important limitation

This does not identify the BMW runtime provider. FUN_007b3820 performs provider
acceptance on the populated runtime matrix, not on the seed-only matrix.
Numeric JOINT/HINGE/BAR coupling may create additional non-zero cells.

The new gate therefore records:

    provider 0 = seed-mask-incompatible, final runtime match requires capture
    provider 1 = dimension-incompatible
    generic fallback = still possible

The first real frame-entry + pre-solve capture remains the authoritative way to
determine which provider, if any, accepts the BMW runtime matrix.
