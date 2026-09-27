# Phase 398 — HINGE/HINGE matrix coupling

`FUN_007bb250` fills the per-body solver matrix for HINGE constraints.

## Self block

For one HINGE sample, `FUN_007aefb0` transforms its angular and linear sample rows. The helper then writes three lower-triangle entries:

- `[base,base] += A·(M A)`;
- `[base+1,base] += A·(M B)`;
- `[base+1,base+1] += B·(M B)`.

The upper off-diagonal entry is not written by this helper.

## Pair block

For two HINGE samples, with the outer sample supplying transformed rows, the source computes `d5=A_j·(M A_i)`, `d6=B_j·(M A_i)`, `d8=A_j·(M B_i)` and `d7=B_j·(M B_i)`. Equal side flags add these values; differing flags subtract them.

The write orientation depends on scalar base order. When inner base < outer base the block is `[[d5,d6],[d8,d7]]`; otherwise it is `[[d5,d8],[d6,d7]]`. This mirrors the exact source address selection.

## Boundary

The phase models only HINGE/HINGE coupling. HINGE/BAR coupling in the same function and BAR/BAR coupling in `FUN_007bb6c0` remain separate targets.
