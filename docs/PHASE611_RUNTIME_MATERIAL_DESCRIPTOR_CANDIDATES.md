# Phase 611 — runtime material-descriptor candidate join

## Purpose

Phase 610 separates stable runtime geometry shapes and resolves 22 of 37 shapes
to one archive-invariant static IMB content candidate. Some remaining geometry
is intentionally identical between materials or LODs, so vertex/index
descriptors alone cannot narrow it further.

Phase 611 adds a conservative material-texture descriptor layer using evidence
that is already present in the old D3D9 capture and the source archives.

## Exact mapping chain

The join never guesses sampler order. For each runtime resource-shape row it
builds the following chain:

```text
exact runtime pixel-shader byte SHA
  -> CTAB sampler name + D3D9 sampler register
  -> exact FX source sampler declaration
  -> SamplerTexture BMT parameter
  -> same-archive BMT DDS path
  -> source DDS descriptor
  -> runtime CreateTexture descriptor at that register
```

Compiled FXO reflection is scanned across the Silverstone visual BFFs plus
`RENDER.bff`, because Phase 565 established that most relevant compiled
permutations live in the visual archives. Byte-identical FXO payload copies are
deduplicated before reflection indexing.

## Descriptor comparison

For BMT-backed compressed DDS resources the exact comparison uses:

- resource type: `texture2d`;
- width;
- height;
- D3D9 FourCC format;
- mip level count.

Only DDS files with an explicit four-character compressed format participate in
the current gate. Unsupported or incomplete static descriptors fail closed and
do not eliminate candidates.

## External sampler policy

A reflected runtime sampler participates only when its CTAB name maps through
the FX source to a BMT texture parameter whose value is an archive-local
`.dds`.

Therefore shadow maps, render targets, global constant textures and cube maps
that are not sourced from the concrete BMT are not treated as material
identity evidence.

## Conservative filtering

The gate narrows a Phase 610 candidate set only when at least one static
content group has a complete BMT-backed material descriptor contract that
matches all of its mapped runtime sampler registers.

If complete material contracts exist but none match the observed runtime
descriptors, the Phase 610 candidate set is retained and the row is reported as
`no-exact-match-fallback`.

This makes descriptor evidence useful for positive narrowing without converting
capture/parser disagreement into a false-negative attribution.

## Known limit

If two content groups use the same BMT payload and the same geometry descriptor
(for example some LOD A/B pairs), material descriptors cannot distinguish them.
That ambiguity is preserved. Closing those pairs requires runtime VB/IB payload
identity or another exact runtime resource-identity channel.

## Boundary

This phase remains candidate-only evidence:

- no runtime resource path is recovered;
- no runtime texture or IMB payload SHA is known;
- pointer identity is not preserved by the normalized report;
- a single surviving content group is not render admission.

Promotion still requires exact runtime resource identity/payload equality and
the existing Phase 572 same-instance/strong-shader gates.

## CLI

```bash
python src/scene/imb_runtime_material_descriptor_candidate_join.py \
  out/d3d9_target_draw_signatures.json \
  out/d3d9_runtime_geometry_shape_candidate_join.json \
  Silverstone_Era3_.zip \
  RENDER.bff \
  out/d3d9_runtime_material_descriptor_candidate_join.json
```
