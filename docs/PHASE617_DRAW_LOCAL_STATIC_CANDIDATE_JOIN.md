# Phase 617 — draw-local static candidate join

Phase 617 consumes the complete offline draw-local evidence produced from the
historical Silverstone D3D9 capture and joins it back to Phase 615 static IMB
candidate sets.

No new game run is required.

## Production input result

The supplied `silverstone_d3d9_target_draw_local_evidence.json` proves that the
existing capture is already complete for the capture-local state needed by this
stage:

- 1,581 target draws;
- 1,581 `strong-capture-local` draws;
- zero `partial-capture-local` draws;
- 55 unique geometry identities;
- all 55 repeated geometry groups distinguished by existing capture state;
- 10 exact captured VS/PS byte-hash pairs;
- 38 texture-object-state signatures;
- 889 vertex-constant signatures;
- 174 pixel-constant signatures.

The same report confirms that the historical capture does **not** contain:

- VB/IB `buffer_payload` events;
- portable `resource_path + resource_sha256` identity pairs;
- captured external texture snapshots.

Those absences do not block Phase 617 because it is a candidate-narrowing stage,
not portable retail-resource promotion.

## Join contract

`src/scene/imb_draw_local_static_candidate_join.py` consumes:

1. `SHIFT.D3D9TargetDrawLocalEvidence/1`;
2. `SHIFT.IMBRuntimeGeometryPointerCandidateJoin/1`.

For every draw it reconstructs the exact pointer-free resource-shape payload used
by Phases 605/613:

- VS byte SHA-256;
- PS byte SHA-256;
- vertex-declaration byte SHA-256;
- stream numbers/strides;
- stream buffer descriptors;
- index-buffer descriptor;
- CTAB-filtered texture descriptors.

It also reconstructs the Phase 613 geometry-pointer identity:

- capture device;
- stream-0 VB pointer + creation generation;
- IB pointer + creation generation;
- exact DrawIndexedPrimitive range.

The preferred join is therefore:

`exact resource-shape SHA + exact geometry-pointer identity SHA`.

If the resource-shape reconstruction cannot match but the geometry identity is
unique in Phase 615, a geometry-only fallback is retained explicitly. If the
same geometry identity occurs under several Phase 615 resource shapes, all
candidate shader variants are preserved and the result remains fail-open.

## Exact shader-byte gate

After a Phase 615 candidate set is located, Phase 617 may reject a candidate only
when an already-recorded static matched shader byte SHA contradicts the exact
shader byte SHA observed at that draw.

Possible gate outcomes include:

- `exact-vs+ps-byte-match`;
- `exact-ps-byte-match`;
- `exact-vs-byte-match`;
- `exact-ps-byte-match-cross-vs-donor`;
- `shader-byte-gate-unavailable`;
- `rejected-pixel-shader-byte-mismatch`;
- `rejected-vertex-shader-byte-mismatch`.

Missing shader identity always fails open.

Phase 612 cross-VS recovery is treated specially: when
`pipeline_recovery_static_vertex_shader_mismatch=true`, the donor VS is
explicitly diagnostic and is never used to reject an otherwise exact PS match.

## Evidence boundary

Even one surviving static content group remains **candidate-only** evidence.
Phase 617 does not claim:

- exact retail IMB identity;
- exact retail primitive identity solely from pointer continuity;
- BMT identity from shared textures;
- FXO permutation identity from ranking;
- scene-instance identity;
- render admission.

Portable IMB promotion still requires either:

- exact runtime resource path/SHA identity; or
- exact captured VB/IB payload equality against the static resource,

plus the existing strong same-instance gates.

## Usage

```bash
python src/scene/imb_draw_local_static_candidate_join.py \
  out/silverstone_d3d9_target_draw_local_evidence.json \
  out/d3d9_runtime_geometry_pointer_candidate_join.json \
  out/silverstone_d3d9_draw_local_static_candidate_join.json
```

The most useful summary fields are:

- `phase615_match_kind_counts`;
- `exact_vs_ps_candidate_draw_count`;
- `single_static_candidate_draw_count`;
- `ambiguous_static_candidate_draw_count`;
- `rejected_static_candidate_variant_count`;
- `candidate_resolution_status_counts`;
- `shader_gate_status_counts`.
