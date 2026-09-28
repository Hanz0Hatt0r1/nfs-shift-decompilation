# Phase 492 — endpoint-aware dynamic contribution schedule

## Goal

Phase 492 refines the Phase 491 dynamic write-domain into an endpoint-aware execution schedule.

A runtime constraint is populated into two BODY endpoint group records. Therefore its self contribution must remain represented once per endpoint BODY, even though the scalar destination cell set is identical.

For each BODY the schedule contains:

- one self operation per populated endpoint group;
- one pair operation for each unordered pair of groups resident in that BODY.

## Kernel ownership

- JOINT-containing operation → `FUN_007bbb80`;
- otherwise HINGE-containing operation → `FUN_007bb250`;
- BAR/BAR → `FUN_007bb6c0`.

## Storage orientation

Self blocks are represented by their lower triangle.

For distinct scalar blocks, the block with the larger scalar base becomes the row domain and the smaller base the column domain. This preserves retail lower-triangle destination addressing independently of record enumeration order.

## Operation vs cell multiplicity

This phase deliberately distinguishes operation count from destination-cell count. Multiple endpoint/group operations can target the same cell and therefore contribute additively during numeric assembly.

`write_cell_count` is the union of unique lower-triangle destination cells.

`lower_triangle_off_diagonal_cell_count` counts unique row>column destinations only.

## Example

For a synthetic 3-constraint domain with one JOINT, one HINGE and one BAR:

- 6 endpoint self operations;
- 3 pair operations across the three shared BODY relationships;
- 21 unique lower-triangle destination cells.

The exact numbers for BMW are intentionally not hard-coded here; the schedule consumes the already reconstructed solver domain.

## Relation to numeric reconstruction

Phase 491 establishes the dynamic write domain. Phase 492 adds operation multiplicity and BODY endpoint ownership. The next numeric layer can now safely evaluate existing kernel formulas and accumulate their blocks without losing which BODY/group operation produced each contribution.

## Scope boundary

No coefficient values are synthesized in this phase. Side-flag sign, transformed vectors, tensor values, and physical interpretation remain in the existing kernel runtimes and their future capture-backed inputs.
