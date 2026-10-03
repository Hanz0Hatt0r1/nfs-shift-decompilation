# Phase 623 — static scene geometry reference join

Phase 623 attacks the Phase 618 geometry-only ambiguity classes before any
request for vertex/index payload capture:

- `metadata-equivalent-lod-siblings`;
- `metadata-equivalent-geometry-alternatives`.

The stage is completely offline and consumes the original BFF/ZIP corpus plus
`SHIFT.IMBDrawLocalAmbiguityAudit/1`.

## Exact source chain

The source-backed SGB parser already reconstructs recursive binary scene
objects:

```text
SGB NODE/SUMM wrapper
-> inline LOD / HIERARCHY / OBJECT
-> recursive subobject reference table
-> OBJECT resource_filename
-> .imb logical resource path
```

For LOD parents it additionally reconstructs:

- child slot index;
- serialized LOD distance for the same child index;
- the proven runtime fallback rule for serialized zero values.

Phase 623 preserves that structure instead of relying on the `_lod*` naming
pattern used only as a Phase 618 diagnostic.

## Resource identity

An SGB OBJECT resource path is joined to a candidate IMB only when the corpus
contains one distinct decoded IMB payload SHA-256 for that exact normalized
logical path and that SHA equals the candidate `imb_sha256`.

Byte-identical duplicate occurrences are retained as provenance. If one exact
path resolves to multiple distinct payload SHAs, the scene reference remains
unresolved; archive ordering is not used to choose a target.

Only SGB files whose source-backed runtime decode is `ready` contribute exact
scene references. Partially decoded SGBs are listed separately and cannot close
this gate.

## LOD families

When two or more surviving candidates are referenced below the same recovered
LOD parent, the draw is classified as:

`source-backed-lod-family-needs-selection-witness`

The report preserves each candidate resource, child slot and serialized
threshold. This proves the alternatives are members of one source LOD family;
it does **not** prove which level produced the captured draw.

A serialized zero threshold is reported as using the source-backed runtime
fallback rule. Phase 623 does not invent the effective value.

## Single static scene reference

If exactly one surviving candidate is referenced by the scanned ready SGB
corpus, the result is:

`single-static-scene-referenced-candidate-unproven-draw`

This deliberately does not populate `selected_content_group_sha256`.
An exact static resource reference is not equivalent to captured draw/instance
identity. An independent instance/spatial/transform or LOD-selection witness is
still required.

Likewise, absence of a scene reference is not treated as an exact contradiction:
the scanned corpus may contain scene roots outside the active captured context.

## Capture boundary

Phase 623 requests no new capture.

The next step for source-backed LOD families is to combine the recovered LOD
slot/threshold contract with an exact scene-instance selection witness from
existing transform/spatial evidence. For a single statically referenced
candidate the next step is to attach an exact scene-instance witness.

Only if geometry identity remains a proven renderer blocker after those joins
should `buffer_payload` or portable runtime resource identity be considered.

## CLI

```bash
python src/scene/imb_static_scene_reference_candidate_join.py \
  out/silverstone_d3d9_draw_local_ambiguity_audit.json \
  out/silverstone_static_scene_reference_candidate_join.json \
  --corpus Silverstone_Era3_.zip \
  --corpus SHIFT_tail.zip
```

Output format:

`SHIFT.IMBStaticSceneReferenceCandidateJoin/1`

The artifact is evidence/classification only and does not authorize render
admission.
