# Phase 634 — offline Phase 618 ambiguity regeneration

Phase 634 removes the last mandatory renderer handoff that still had to arrive as
a prebuilt report: `SHIFT.IMBDrawLocalAmbiguityAudit/1`.

The report is now reproducible from evidence already available in the project:

- the historical raw D3D9 JSONL capture;
- the committed/runtime Silverstone shader target set;
- Phase 630 draw-local evidence;
- the static Silverstone IMB/BMT/DDS corpus;
- `render.bff`, either directly or inside a ZIP.

The original game is never launched and no new capture is requested.

## Orchestrator

`tools/run_silverstone_renderer_ambiguity_regeneration.py` composes existing
proof stages without changing their semantics:

```text
historical raw D3D9 JSONL
  → Phase 605 target draw-signature catalog
  → Phase 613 target pointer observations

Silverstone source archive
  → Phase 562 IMB corpus audit

runtime catalog + shader targets
  → Phase 609 runtime pipeline candidates

runtime catalog + pipeline candidates + IMB corpus
  → Phase 610/612 runtime geometry-shape candidates

runtime catalog + geometry candidates
+ Silverstone BMT/DDS corpus + render FX/FXO
  → Phase 611 material-descriptor candidates

pointer observations + material candidates
  → Phase 615 runtime geometry-pointer candidates

Phase 630 draw-local evidence + Phase 615
  → Phase 617 draw-local static candidate join

Phase 617
  → Phase 618 draw-local ambiguity audit
```

The top-level manifest format is:

```text
SHIFT.SilverstoneRendererAmbiguityRegeneration/1
```

## Produced reports

The output directory retains every intermediate proof artifact:

```text
d3d9_target_draw_signature_catalog.json
  SHIFT.D3D9TargetDrawSignatureCatalog/1

d3d9_target_pointer_observations.json
  SHIFT.D3D9TargetPointerObservations/1

imb_corpus_audit.json
  SHIFT.IMBCorpusAudit/1

imb_runtime_pipeline_candidate_join.json
  SHIFT.IMBRuntimePipelineCandidateJoin/1

imb_runtime_geometry_shape_candidate_join.json
  SHIFT.IMBRuntimeGeometryShapeCandidateJoin/1

imb_runtime_material_descriptor_candidate_join.json
  SHIFT.IMBRuntimeMaterialDescriptorCandidateJoin/1

imb_runtime_geometry_pointer_candidate_join.json
  SHIFT.IMBRuntimeGeometryPointerCandidateJoin/1

imb_draw_local_static_candidate_join.json
  SHIFT.IMBDrawLocalStaticCandidateJoin/1

imb_draw_local_ambiguity_audit.json
  SHIFT.IMBDrawLocalAmbiguityAudit/1
```

The manifest records the status, format and SHA-256 of each emitted stage.

## Runtime catalog and pointer alignment

The runtime draw catalog and pointer-observation report are regenerated from the
same historical JSONL and target inventory.

Phase 613 is given the newly generated target catalog as its alignment source.
The resulting `catalog_alignment.status` must be `exact`; otherwise the chain is
blocked before Phase 615.

Pointer equality remains session-local evidence only. It is never promoted to a
portable retail resource identity.

## Static corpus gate

`audit_imb_corpus()` is run directly against the supplied Silverstone BFF or ZIP.
The geometry chain proceeds only when the selected IMB corpus is completely
ready.

A partial corpus does not cause a candidate to be dropped. Instead:

```text
corpus audit remains available
→ geometry/material/pointer narrowing is blocked
→ Phase 618 is not produced
```

This preserves the fail-closed policy.

## render.bff selection

The Phase 611 material-descriptor stage needs the render FX source archive.
Phase 634 accepts either:

- `render.bff` directly; or
- a ZIP containing it.

For ZIP input the selection rule is deliberately strict:

```text
exactly one archive entry whose basename, case-insensitively, is render.bff
```

Zero matches or more than one match is an ambiguity and blocks the material
stage. Filename ranking, archive order and frequency are not used.

The selected ZIP entry name, size and SHA-256 are recorded in the manifest.

## No target draws

If the historical capture contains no target draws, the runtime catalog can
still be emitted for diagnostics, but the top-level manifest remains blocked:

```text
runtime_catalog:no-target-draws-observed
```

Even if mocked or partial downstream tools can technically emit reports, this
condition can never yield `ready=true`.

## Proof boundary

Phase 634 preserves all previous limitations:

- Phase 609/610/611/615/617 results are candidate narrowing, not render
  admission;
- capture-local pointer identity is not portable resource identity;
- a single remaining candidate is not automatically a proven retail resource;
- zero-match evidence never invents a candidate;
- ranking, frequency and archive order are not proof;
- missing historical capture events do not imply a new capture;
- exact VB/IB `buffer_payload` equality remains only a last conditional fallback
  for geometry alternatives that survive all static/scene evidence;
- no new sampler-state/path-SHA/texture-snapshot observation is fabricated;
- original executable execution is not required.

## CLI

Example using the existing project corpus:

```bash
python tools/run_silverstone_renderer_ambiguity_regeneration.py \
  --capture-jsonl shift_d3d9_capture.jsonl \
  --draw-local out/raw/d3d9_target_draw_local_evidence.json \
  --source-archive Silverstone_Era3_.zip \
  --render-archive SHIFT_tail.zip \
  --output-dir out/silverstone_phase618
```

The committed `evidence/silverstone_era3_runtime_shader_targets.json` is used by
default unless an explicit target report is supplied.

## Regression coverage

`tests/test_run_silverstone_renderer_ambiguity_regeneration.py` verifies:

- the full nine-stage offline chain reaches Phase 618;
- ZIP render selection requires one exact basename `render.bff`;
- a partial IMB corpus blocks all geometry-dependent downstream stages;
- ambiguous render ZIPs fail closed before material correlation;
- zero observed target draws can never produce a ready manifest;
- no game execution, new capture request or ranking-based proof is introduced.

## Next

Once this regeneration path is green, the production integration can treat a
bundle Phase 618 report exactly like the other regenerated handoffs:

- regenerated ambiguity becomes the production source;
- a bundle copy, when present, is only a canonical SHA cross-check;
- absence of a bundle ambiguity report is allowed;
- mismatch blocks production;
- multiple historical variants can only be disambiguated by exact regenerated
  canonical identity.

At that point the renderer production path no longer requires any prebuilt JSON
handoff bundle for its core Phase 619–626 execution.
