# Phase 416 — SDF runtime probe session bridge

Phase 415 produces independent pre-solve and post-solve JSON files. Phase 416 turns them into a single deterministic session record.

## Pairing

`normalize_probe_session()` checks scalar-count consistency and, when both probes expose frame indices, requires the same frame number.

The pre-solve record is passed through the Phase 411 normalized capture schema, so its 40×40 matrix and 40-value RHS remain directly comparable.

The post-solve record is treated as the solved scalar vector captured at `FUN_007b4110`.

## Numeric validation

`compare_probe_session()` compares the pre-solve matrix/RHS with an expected capture through the Phase 411 cell-level comparator and separately compares the post-solve vector. A missing post-solve capture is a blocking mismatch when the expected session contains one.

The CLI is `tools/verify_sdf_probe_session.py`.

No runtime capture is fabricated or stored in the repository by this phase.