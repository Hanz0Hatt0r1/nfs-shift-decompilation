# Phase 610 — runtime geometry-shape candidate join

## Purpose

Phase 609 removes archive-copy inflation from static pipeline candidates, but a
single D3D9 shader pipeline legitimately renders multiple different meshes.
Therefore a pipeline is too coarse a unit for expecting one IMB candidate.

Phase 610 moves the correlation boundary down to the stable geometry resource
shape already present in `SHIFT.D3D9TargetDrawSignatureCatalog/1`.

## Runtime geometry identity

For each Phase 605 resource-shape row the tool removes texture descriptors and
the dynamic instance-stream resource. The stable geometry key contains:

- pointer-free pipeline signature;
- stream-0 vertex-buffer descriptor;
- index-buffer descriptor;
- complete observed draw-range set.

Resource rows that differ only in reflected texture descriptors collapse to one
geometry shape.

## Static geometry correlation

The tool consumes the existing `SHIFT.IMBCorpusAudit/1` output and indexes
ready IMBs by decoded payload SHA-256. This supplies source-backed:

- vertex count;
- primitive-record count;
- total triangle/index count.

For D3D9 INDEX16/INDEX32 descriptors it derives runtime index count from buffer
length. Runtime stream-0 vertex count is derived only when buffer length divides
exactly by stride.

A content candidate is an exact descriptor match only when:

1. the Phase 609 content group matches the shape's complete draw range;
2. the primitive draw covers the complete source IMB index list;
3. runtime stream-0 length/stride equals the source IMB vertex count;
4. runtime index-buffer length/format equals the source IMB index count.

The descriptor filter is conservative: it narrows only when at least one exact
static descriptor match exists. If complete descriptors exist but none match,
the range-matched candidate set is preserved and the row is marked
`no-exact-match-fallback`.

## Boundary

This remains candidate-only evidence. The capture does not preserve runtime
buffer payloads, resource paths, payload SHA-256 or resource-pointer to IMB
identity. A single content candidate therefore does not satisfy same-instance
identity or render admission.

Phase 572/574 promotion still requires exact runtime IMB resource identity,
exact primitive draw identity and the existing strong shader gates.

## CLI

First build the already-supported source corpus audit:

```bash
python tools/audit_imb_corpus.py \
  Silverstone_Era3_.zip \
  -o out/silverstone_imb_corpus_audit.json \
  --require-all-ready
```

Then correlate the existing Phase 605/609 reports:

```bash
python src/scene/imb_runtime_geometry_shape_candidate_join.py \
  out/d3d9_target_draw_signatures.json \
  out/d3d9_runtime_pipeline_candidate_join.json \
  out/silverstone_imb_corpus_audit.json \
  out/d3d9_runtime_geometry_shape_candidate_join.json
```
