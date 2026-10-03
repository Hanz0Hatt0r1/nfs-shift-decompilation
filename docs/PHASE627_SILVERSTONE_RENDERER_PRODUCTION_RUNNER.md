# Phase 627 — Silverstone renderer production runner

Phase 627 turns the already-implemented exact renderer evidence stages into one
repeatable production command. It adds **orchestration only**: no new candidate
ranking, identity heuristic, proof rule, or capture interpretation is introduced.

## Tool

`tools/run_silverstone_renderer_production.py` executes the existing chain:

```text
Phase 618 ambiguity audit + runtime shader targets + corpus
  -> Phase 619 exact FXO pair provenance
  -> Phase 620 exact material constant candidate join
  -> Phase 622 exact material texture candidate join

Phase 618 ambiguity audit + corpus
  -> Phase 623 static scene reference candidate join
  + existing runtime capture pipeline
  -> Phase 624 exact runtime resource/draw join
  + existing SGB runtime object candidate join, only when repeated placements exist
  -> Phase 625 exact repeated-instance transform join

base renderer requirement audit + all available exact reports
  -> Phase 626 renderer frontier
  -> SHIFT.SilverstoneRendererProductionRun/1
```

The runner calls the existing Python builders directly in one process. It does
not shell out to the original game, launch `SHIFT.exe`, or collect a new
capture.

## Inputs

The command takes explicit report paths:

- `SHIFT.D3D9RendererRequirementAudit/1`;
- `SHIFT.IMBDrawLocalAmbiguityAudit/1`;
- `SHIFT.IMBRuntimeShaderTargetSet/1`;
- `SHIFT.D3D9TargetDrawLocalEvidence/1`;
- `SHIFT.IMBRuntimeCapturePipeline/1`;
- optional `SHIFT.SGBRuntimeObjectCandidateJoin/1`;
- one or more original BFF/ZIP corpus inputs.

The runtime shader target set defaults to the committed
`evidence/silverstone_era3_runtime_shader_targets.json`. Every other report path
is explicit so a similarly named or stale file cannot be silently substituted.

The object-candidate join is optional only at invocation time. If Phase 624
finds one or more `exact-resource-draw-repeated-scene-instance` rows, Phase 625
requires this input and the production run reports an offline input blocker when
it is absent. If no repeated instances exist, Phase 625 is recorded as
`not-needed`.

## Outputs

The output directory receives the conventional production files:

- `silverstone_fxo_pair_provenance.json`;
- `silverstone_material_constant_candidate_join.json`;
- `silverstone_material_texture_candidate_join.json`;
- `silverstone_static_scene_reference_candidate_join.json`;
- `silverstone_runtime_resource_draw_candidate_join.json`;
- `silverstone_repeated_scene_instance_transform_join.json` when Phase 625 is applicable;
- `silverstone_renderer_frontier_audit.json`;
- `silverstone_renderer_production_run.json`.

`silverstone_renderer_production_run.json` uses:

- `SHIFT.SilverstoneRendererProductionRun/1`.

It records SHA-256 and size for every present input report and corpus file, each
stage output SHA-256, stage status/summary, exact blocking reasons, and the final
renderer frontier's existing-data work, genuinely absent capture observations,
conditional capture observations, and hard capture blockers.

JSON stage outputs are written atomically.

## Fail-closed policy

A missing/invalid report, corpus file, wrong report format, or stage exception is
recorded as a production blocker. It never:

- removes a candidate;
- selects a tied candidate;
- supplies a default resource identity;
- treats descriptor similarity as texture identity;
- infers a LOD from a path name;
- treats missing VB/IB payload as a current capture request.

Independent stages still run when their own inputs are complete, so the manifest
shows exactly how far the existing evidence can progress.

The runner deliberately preserves the Phase 619-626 proof boundaries. In
particular:

- ranking is not proof;
- incomplete candidates are not contradictions;
- repeated scene instances are selected only by the existing exact transform
  gate;
- `buffer_payload` stays a last conditional fallback;
- historical absence of `SetSamplerState`, portable texture path+SHA, texture
  snapshots, or buffer payload stays historical capture metadata rather than an
  automatic new-capture request.

## Production invocation

Example using the existing Silverstone artifacts:

```bash
python tools/run_silverstone_renderer_production.py \
  --output-dir out/silverstone_renderer_production \
  --base-audit out/d3d9_renderer_requirement_audit.json \
  --ambiguity-audit out/silverstone_d3d9_draw_local_ambiguity_audit.json \
  --draw-local out/d3d9_target_draw_local_evidence.json \
  --capture-pipeline out/silverstone_imb_runtime_capture_pipeline.json \
  --object-candidate-join out/silverstone_sgb_runtime_object_candidate_join.json \
  --corpus Silverstone_Era3_.zip \
  --corpus SHIFT_tail.zip
```

If the actual capture-pipeline/object-join filenames differ, pass their exact
paths. Do not rename an unrelated report merely to satisfy the example; the
runner checks the embedded format before execution.

A completed runner invocation means only that every applicable orchestration
stage executed. Renderer closure remains the Phase 626 frontier's conclusion.
`renderer_capture_required_now` is copied from that frontier and is never
inferred from runner-level missing inputs.

## Regression coverage

`tests/test_run_silverstone_renderer_production.py` covers:

- a complete Phase 619-626 production chain with repeated-instance closure;
- SHA-256 provenance for corpus and generated stage files;
- repeated-instance object-join absence as an offline input blocker;
- Phase 625 `not-needed` behavior when no repeated placements remain;
- input format mismatch propagation;
- stage exceptions remaining explicit blockers rather than candidate evidence.
