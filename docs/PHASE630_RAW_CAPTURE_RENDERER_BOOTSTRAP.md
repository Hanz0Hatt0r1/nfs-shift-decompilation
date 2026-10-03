# Phase 630 — raw capture renderer bootstrap

Phase 630 removes two more manually prepared renderer handoff reports from the
Silverstone production path.

It consumes the already existing historical D3D9 JSONL capture and static PE
evidence. It does **not** run the original game and it does not request a new
capture.

## Pipeline

`tools/run_silverstone_renderer_raw_capture_bootstrap.py` executes:

```text
SHIFT.PEImageEvidence/1
→ exact decoded D3D9 Usage ordinal map

historical shift_d3d9_capture.jsonl
+ SHIFT.IMBRuntimeShaderTargetSet/1
→ target draw-local evidence

same parsed historical capture events
+ exact Usage map
+ same target set
→ Phase 573 IMB runtime capture pipeline
```

Outputs are:

- `d3d9_usage_map.json` — `SHIFT.D3D9UsageMap/1`;
- `d3d9_target_draw_local_evidence.json` —
  `SHIFT.D3D9TargetDrawLocalEvidence/1`;
- `silverstone_imb_runtime_capture_pipeline.json` —
  `SHIFT.IMBRuntimeCapturePipeline/1`;
- `silverstone_renderer_raw_capture_bootstrap.json` —
  `SHIFT.SilverstoneRendererRawCaptureBootstrap/1`.

The target-set CLI default is the existing committed
`evidence/silverstone_era3_runtime_shader_targets.json`.

## Usage map proof boundary

The declaration gate requires the game's internal Usage ordinal to D3D9 Usage
numeric mapping.

Phase 630 does not infer this mapping from semantic names, declaration frequency,
or runtime similarity. It calls `build_d3d9_usage_map()` and accepts only the
nine decoded values from:

`SHIFT.PEImageEvidence/1:decoded_tables.usage`.

All ordinals `0..8` must be present for `SHIFT.D3D9UsageMap/1.ready = true`.
A missing ordinal is a missing static evidence value, not a declaration
contradiction.

## One capture parse

The historical JSONL is parsed once with the existing
`d3d9_runtime_trace.load_events(..., skip_unsupported=True)` path.

The same resulting event sequence is reused by:

1. `build_target_draw_local_evidence()`;
2. `build_imb_runtime_capture_pipeline()`.

This avoids two independent parses of the large historical capture and ensures
both reports observe exactly the same accepted event stream.

## Partial-output policy

Draw-local evidence does not depend on the numeric Usage map.

Therefore, when PE evidence is missing or the Usage map is partial:

- `SHIFT.D3D9TargetDrawLocalEvidence/1` is still generated when the capture and
  runtime target set are valid;
- `SHIFT.IMBRuntimeCapturePipeline/1` is not run;
- the bootstrap remains `blocked`;
- no candidate is rejected because the Usage map is missing.

Likewise, a valid Usage map is still persisted when capture parsing fails.

This is intentional evidence preservation, not partial proof promotion.

## Usage

```bash
python tools/run_silverstone_renderer_raw_capture_bootstrap.py \
  shift_d3d9_capture.jsonl \
  out/shift_pe_image_evidence.json \
  --output-dir out/silverstone_renderer_raw_capture
```

An explicit target set can be supplied with:

```bash
--runtime-shader-targets evidence/silverstone_era3_runtime_shader_targets.json
```

## Relationship to Phase 629

Phase 629 currently accepts compact report bundles such as `out.zip` and feeds
normalized reports into the Phase 627 production runner.

Phase 630 reconstructs two of those compact inputs directly from original
historical evidence:

- `draw_local`;
- `capture_pipeline`.

A later orchestration stage can combine Phase 630 outputs with the remaining
bundle/static inputs (`base_audit`, Phase 618 ambiguity audit, and optional
object-candidate join) and can cross-check a bundle-provided compact report
against a freshly regenerated report rather than silently selecting one.

## Capture boundary

Phase 630 does not change the known historical capture facts. In particular,
the old capture still lacks direct observations for:

- `SetSamplerState`;
- VB/IB `buffer_payload`;
- portable runtime resource path+SHA events;
- texture payload snapshots.

Their absence remains conditional evidence. Phase 630 does not convert any of
these into a request for another capture.

## Regression coverage

`tests/test_run_silverstone_renderer_raw_capture_bootstrap.py` verifies:

- a fully ready PE map drives both derived reports;
- the raw capture parser is called once and the accepted event sequence is
  reused;
- string JSON Usage-map keys are converted to exact integer ordinals for Phase
  573;
- a partial Usage map still preserves draw-local evidence while blocking the
  runtime pipeline;
- an invalid PE evidence format fails closed without destroying independent
  draw-local evidence;
- an invalid runtime target set prevents capture parsing;
- a capture parse failure is preserved as a blocker while a valid static Usage
  report remains available.
