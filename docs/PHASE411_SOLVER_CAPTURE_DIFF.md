# Phase 411 — SDF solver capture diff

This phase adds a strict input schema and cell-level comparator for a real captured SHIFT SDF solver frame.

## Capture shape

A normalized capture contains:

- `scalar_count` — number of solver scalar nodes;
- `rhs` — `scalar_count` doubles;
- `matrix` — `scalar_count × scalar_count` doubles;
- optional `row_indices`, `runtime_identity_nodes`, frame/source identifiers and metadata.

## Comparison

The comparator reports exact vector and matrix mismatch locations with absolute and relative errors. It also verifies the retail row-index shape (`scalar_count * row`) and emits normalized SHA-256 fingerprints.

The comparator intentionally does not synthesize missing values from a trace. It is an ingestion/validation boundary: once a real runtime dump is available, it can be compared against the reconstructed 40-scalar model without changing the file format.

No real solver capture is committed by this phase.