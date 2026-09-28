# Phase 490 — provenance-backed BMW seed parity

## Goal

Phase 490 combines the Phase 486 structural matrix builder with the Phase 489 cell-provenance layer and the canonical BMW Phase 406 seed shape.

The result answers two independent questions:

1. does every structural non-zero cell have at least one source-backed BODY/group provenance witness?
2. does the generated 40×40 support have the expected BMW seed shape?

## Provenance consistency

The verifier rejects any generated non-zero cell without provenance and any provenance cell whose generated matrix value is zero. It also checks that each witness's stored source/target scalar indices equal the actual cell coordinates.

This turns a structural matrix into an explainable graph rather than a bare 0/1 array.

## BMW seed shape

The canonical BMW target remains:

- 40 scalar dimensions;
- 700 non-zero cells;
- 900 zero cells;
- 330 strict-upper non-zero cells;
- row non-zero counts `[10 × 10, 25 × 20, 10 × 10]`.

Phase 487 additionally uses the full flattened 0/1 SHA-256 `6d066aab...`; Phase 490 intentionally keeps this layer shape-oriented because provenance is the primary purpose of this phase.

## Interpretation

A complete provenance graph plus matching BMW shape establishes that the structural seed is explainable and has the expected aggregate topology. It still does not establish exact byte-hash equality unless Phase 487's hash gate is also passed, and neither result establishes provider numeric parity.

## Scope boundary

No physical semantics are assigned to scalar cells. Provider identity remains capture-gated, and dynamic coefficient accumulation remains outside this phase.
