# Phase 405 — real BMW M3 solver scalar domain

The actual `BMW_M3_E36.bff` intake from Phase 404 is now connected to the reconstructed SDF ordering/runtime topology.

The decoded `vehicles/physics/suspension/aarm_multilink.sdf` contains 24 source constraint records: four `JOINT&HINGE` records and twenty BAR records. `FUN_007b3150` materializes each `JOINT&HINGE` as one JOINT runtime record plus one HINGE runtime record, producing 28 runtime constraint records in total.

Using the source-backed solver widths JOINT=3, HINGE=2 and BAR=1, the real asset therefore occupies exactly 40 scalar solver nodes. `FUN_007b1b60`'s ordering heuristic preserves the source order except for the two final wheel pairs, resulting in the final runtime order tail `[25,24,27,26]` and reducing the recovered block-distance objective from 17516 to 17296.

The Phase 403 storage contract maps these 40 scalar nodes to a 40×40 double matrix (12,800 bytes) and a 40-entry row-pointer table (160 bytes). The runtime domain helper exposes every record's scalar base/end range so later captured solver vectors and matrix rows can be compared by exact scalar index instead of relying on inferred names.

This phase intentionally stops at topology/index mapping. It does not invent runtime state, body-frame values or physical units, so the coefficient values in the assembled matrix remain a separate captured-runtime validation target.
