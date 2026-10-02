# Phase 615: geometry-pointer candidate join

Phase 614 tested exact combined runtime object identity (stream-0 VB + IB + CTAB-filtered textures) against Phase 611 single-content candidates. On the historical Silverstone capture it produced 55 combined identities covering all 1,581 target draws, but no ambiguous identity reused an exact combined identity from a single-content row.

Phase 615 deliberately weakens only the runtime continuity key, not the static candidate contract. It uses Phase 613 **geometry pointer identity** independently from material texture identity:

- capture device;
- stream-0 vertex-buffer COM pointer plus CreateVertexBuffer generation;
- index-buffer COM pointer plus CreateIndexBuffer generation;
- exact runtime DrawIndexedPrimitive range.

A Phase 611 `single-content-candidate` row seeds a static geometry fingerprint made from:

- exact decoded IMB SHA-256;
- primitive index;
- source primitive first/index/triangle counts;
- static source-derived vertex stride.

If an ambiguous resource shape observes the same capture-local geometry allocation, only candidate content groups carrying that exact geometry fingerprint may survive. Conflicting seeds fail open. A seed that is absent from the ambiguous row's static candidate set also fails open.

## Why material pointers do not narrow

Phase 613 also preserves CTAB-filtered texture-object generations. Phase 615 does **not** map equal texture objects to BMT identity because distinct materials may share the same DDS resources while differing in constants or other material state. Texture continuity remains diagnostic.

## Evidence boundary

Geometry-pointer equality proves only object continuity inside one capture session. It does not prove archive path, IMB payload bytes, portable resource identity, scene instance identity, or render admission. Phase 615 is candidate-only evidence.

Promotion still requires exact runtime resource path/SHA or payload equality plus the existing Phase 572 strong same-instance gates.

## Usage

```bash
python src/scene/imb_runtime_geometry_pointer_candidate_join.py \
  out/d3d9_target_pointer_observations.json \
  out/d3d9_runtime_material_descriptor_candidate_join.json \
  out/d3d9_runtime_geometry_pointer_candidate_join.json
```

The most useful summary fields are:

- `newly_resolved_geometry_identity_count`;
- `newly_resolved_geometry_identity_draw_count`;
- `seeded_geometry_identity_observation_count`;
- `geometry_seed_conflict_identity_count`;
- `geometry_candidate_gate_status_counts`.
