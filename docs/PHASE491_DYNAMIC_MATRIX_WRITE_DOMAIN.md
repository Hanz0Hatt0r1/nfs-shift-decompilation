# Phase 491 — dynamic matrix write domain

## Goal

Phase 491 enumerates the destination-cell domain of the already reconstructed dynamic SDF coupling kernels without evaluating coefficient values.

## Self blocks

Each runtime constraint writes its own lower-triangle self block:

- JOINT: 3×3 lower triangle → `FUN_007bbb80`;
- HINGE: 2×2 lower triangle → `FUN_007bb250`;
- BAR: 1×1 → `FUN_007bb6c0`.

The scalar block comes directly from the ordered solver-domain `scalar_base` and `solver_width`.

## Pair blocks

Two runtime constraints are pair-connected when their `posbody`/`negbody` endpoint sets share a BODY, matching the recovered connectivity rule from `FUN_007b1b60`.

For a pair of distinct scalar blocks, the block with the larger scalar base becomes the lower-triangle row-domain and the smaller base becomes the column-domain. This yields exact destination cells without depending on the order in which the two constraints were enumerated.

Kernel ownership follows the existing source decomposition:

- any pair involving JOINT → `FUN_007bbb80`;
- otherwise any pair involving HINGE → `FUN_007bb250`;
- BAR/BAR → `FUN_007bb6c0`.

## Output

The runtime reports:

- self-cell count;
- pair-cell count;
- union write-cell count;
- lower-triangle off-diagonal cell count;
- per-kernel write counts;
- per-cell provenance identifying the source constraint pair and shared BODY.

## Relation to earlier phases

Phase 489 explains the structural `FUN_007ba2b0` seed cells.

Phase 491 explains the later coefficient-bearing destination domain used by `FUN_007bbb80`, `FUN_007bb250` and `FUN_007bb6c0`.

Together they separate:

`structural seed provenance → dynamic coupling write domain → numeric coefficient evaluation`

## Scope boundary

This phase intentionally does not evaluate coefficient formulas, side signs, transformed vectors, or physical quantities. Those remain in the individual kernel modules already present in the repository.

It also does not claim that every dynamic destination is non-zero for every runtime frame; only the source-supported write domain is enumerated.
