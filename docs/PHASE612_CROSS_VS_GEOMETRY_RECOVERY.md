# Phase 612 — cross-VS geometry candidate recovery

## Purpose

Phase 611 showed that three foliage resource shapes still had no geometry
candidates even though their D3D9 buffer descriptors were complete. The failure
occurred one layer earlier: the exact runtime pipeline had no static content
groups.

A second observed foliage pipeline already has strong static
`exact-vs+ps` candidates while sharing the same pixel shader and D3D9 input
layout. Phase 612 uses that sibling pipeline as a candidate donor without
claiming that its vertex shader is the target vertex shader.

## Recovery key

Recovery is attempted only when the exact runtime pipeline has zero static
content groups.

A donor pipeline must:

- be present in the same runtime capture;
- have static candidate evidence beginning with `exact-vs+ps`;
- have the exact same pixel-shader byte SHA-256;
- have the exact same vertex-declaration SHA-256;
- have the exact same stream number/stride layout;
- have the exact same index format.

Only the vertex-shader byte SHA-256 may differ.

All qualifying donor content groups are unioned by content-group identity. The
donor pipeline signature(s) are retained on each recovered group.

## Target-specific gates still apply

Recovered groups are not accepted merely because a sibling pipeline saw them.
The existing Phase 610 gates are rerun against the target geometry shape:

1. complete target draw-range match;
2. source-backed IMB geometry lookup;
3. full-mesh draw requirement;
4. exact runtime stream-0 vertex count;
5. exact runtime index-buffer count.

If no recovered candidate passes those gates, no candidate is fabricated.

## Vertex shader boundary

The donor's static vertex-shader SHA remains diagnostic evidence only.

Every recovered group records:

- `pipeline_recovery_evidence_kind`;
- `relaxed_pipeline_donor_signature_sha256s`;
- `pipeline_recovery_runtime_vertex_shader_sha256`;
- `pipeline_recovery_static_vertex_shader_mismatch`.

A mismatch is expected for the Phase 612 use case and explicitly prevents this
path from being interpreted as VS attribution.

## Output additions

`SHIFT.IMBRuntimeGeometryShapeCandidateJoin/1` gains:

Per geometry shape:

- `pipeline_candidate_source`;
- `direct_pipeline_content_group_count`;
- `relaxed_pipeline_donor_count`.

Summary:

- `relaxed_pipeline_recovery_geometry_shape_count`;
- `relaxed_pipeline_recovery_draw_count`;
- `relaxed_pipeline_recovery_candidate_geometry_shape_count`.

The format version is intentionally unchanged because the existing contract is
extended additively and all prior fields retain their meaning.

## Boundary

This remains candidate-only evidence.

Cross-VS recovery does **not** prove:

- target runtime VS identity;
- runtime IMB path or SHA;
- runtime resource pointer identity;
- same-instance attribution;
- render admission.

Promotion still requires exact runtime resource identity or payload equality
plus the existing Phase 572 strong same-instance gates.

## Re-run

After updating the repository, regenerate Phase 610 and then Phase 611:

```bash
python src/scene/imb_runtime_geometry_shape_candidate_join.py \
  out/d3d9_target_draw_signatures.json \
  out/d3d9_runtime_pipeline_candidate_join.json \
  out/silverstone_imb_corpus_audit.json \
  out/d3d9_runtime_geometry_shape_candidate_join.json

python src/scene/imb_runtime_material_descriptor_candidate_join.py \
  out/d3d9_target_draw_signatures.json \
  out/d3d9_runtime_geometry_shape_candidate_join.json \
  Silverstone_Era3_.zip \
  RENDER.bff \
  out/d3d9_runtime_material_descriptor_candidate_join.json
```
