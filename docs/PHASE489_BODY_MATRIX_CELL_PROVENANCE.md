# Phase 489 — BODY matrix cell provenance

## Goal

Phase 489 makes every structural non-zero matrix cell explainable from the BODY scalar-group population evidence.

For each BODY, the runtime keeps the ordered scalar groups contributed by JOINT/HINGE/BAR records. The provenance layer expands the same Cartesian products used by `FUN_007ba2b0` and records, for each `(row,column)`, which BODY and which source/target group pair produced the `1.0` write.

## Provenance record

Each producer entry retains:

- BODY name;
- source and target group positions within that BODY;
- ordered runtime constraint positions/indices;
- source/target endpoint fields (`posbody` or `negbody`);
- source/target section (`JOINT`, `HINGE`, `BAR`);
- exact source and target scalar indices;
- the seed value `1.0`.

A cell may have multiple producers when multiple constraint groups incident on the same BODY generate the same ordered cell.

## Structural checks

The layer validates that every provenance key is inside the scalar domain, every provenance value is exactly `1.0`, and the stored source/target scalar indices agree with the matrix-cell key.

The number of provenance keys is also checked against the reported structural non-zero cell count.

## Relation to BMW seed parity

Phase 487 verifies the full BMW 40×40 structural seed by counts, row cardinalities, symmetry, and the Phase 406 0/1 byte hash.

Phase 489 adds the missing explanatory layer: when a cell differs from the expected seed, the next diagnostic step can identify which BODY/group relationship generated or failed to generate that cell.

## Important boundary

Provenance explains structural support only. It does not identify physical meaning, coefficient values after later accumulation, or provider identity.

The provenance report is therefore deliberately separate from the numerical provider solver and from the acceptance RLE masks.
