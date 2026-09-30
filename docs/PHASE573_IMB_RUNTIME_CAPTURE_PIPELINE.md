# Phase 573 — IMB runtime capture orchestration

Phase 572 implements exact same-instance shader-variant matching for one IMB
resource runtime report. Phase 573 connects the previously separate capture
stages into one fail-closed Silverstone attribution pipeline.

## Contract

The new contract is:

`SHIFT.IMBRuntimeCapturePipeline/1`

implemented in:

`src/scene/imb_runtime_capture_pipeline.py`.

The pipeline consumes:

- `SHIFT.IMBRuntimeShaderTargetSet/1`;
- one raw native D3D9 JSONL capture;
- the recovered source-Usage-ordinal → D3D9-Usage numeric map.

## Execution order

The orchestration is:

```text
raw D3D9 JSONL
  → Phase 569 shader prefilter
  → shader-candidate bindings
  → exact source-backed primitive draw-range routing
  → candidate exact IMB resources
  → D3D9RuntimeBindingEvidence/1 per candidate resource
  → Phase 572 same-instance shader-variant matcher
```

No stage replaces a stronger downstream proof with an earlier heuristic.

## Draw-range routing

Phase 569 deliberately does not claim primitive or resource identity. Its
candidate draw contains shader-compatible binding indices.

Phase 573 applies a second cheap routing filter:

- raw `start_index` must equal the source IMB `first_index`;
- raw `primitive_count * 3` must equal source `index_count`.

Bindings failing this equality are discarded before expensive runtime resource
reconstruction.

This routing still does **not** prove resource identity. Different IMBs may
share both a shader and a draw range.

Exact resource/declaration proof remains inside
`SHIFT.D3D9RuntimeBindingEvidence/1`.

## Candidate-resource execution

`SHIFT.IMBRuntimeResourceEvidenceSet/1` groups bindings by exact archive +
IMB path + decoded SHA-256.

Only resource groups intersecting the routed binding set are sent through the
full D3D9 runtime evidence builder.

This prevents the same raw capture from being reconstructed against every
Silverstone IMB when the shader/range evidence already rules most resources
out.

## Usage map

The D3D9 declaration gate needs the recovered internal Usage ordinal → numeric
D3D9 Usage mapping.

Phase 573 therefore keeps the pipeline fail-closed when no Usage map is
provided:

`usage-ordinal-map:not-supplied`.

Shader prefilter/routing results remain useful, but
`pipeline_ready = false` until declaration correlation can be evaluated.

## Compact output

Full D3D9 runtime frame state can be large. The orchestrator uses it internally
for Phase 572 matching but stores only a compact per-resource runtime summary:

- runtime status and trace counts;
- same-instance gate readiness/candidate count/blockers;
- Phase 572 candidate-binding results.

The output explicitly records that full runtime frames are not retained.

## Readiness

`pipeline_ready` means all static/capture-preparation contracts are valid and
the Usage map is available.

`attribution_complete` is stricter: every binding routed from the observed
candidate draws is uniquely attributed by the Phase 572 strong-evidence gate.

Possible output states are:

- `blocked` — structural/evidence prerequisite missing;
- `not-found` — capture contains no shader+draw-range compatible binding;
- `not-attributed` — candidates exist but no runtime binding is observed;
- `partial` — some routed bindings are observed/attributed;
- `ready` — every routed binding is uniquely attributed.

## CLI

```bash
python src/scene/imb_runtime_capture_pipeline.py \
  out/silverstone-runtime-shader-targets.json \
  shift_d3d9_capture.jsonl \
  out/silverstone-runtime-attribution.json \
  --usage-map d3d9_usage_map.json
```

## Boundary

Phase 573 makes the Silverstone runtime shader-attribution path executable end
to end once a real capture is supplied. It does not generate runtime evidence
synthetically and does not promote pixel-only shader hits.

The remaining external evidence gate is an authentic Silverstone D3D9 capture
containing the relevant rendered track resources.

## Next

After the first authentic capture:

1. execute this pipeline and freeze uniquely attributed FXO/VS/PS identities;
2. feed proven shader selections back into generic RenderBinding/RenderCommand;
3. connect admitted Silverstone scene geometry to `native_runtime`;
4. continue the independent IMX and SceneGraph transform-history workstreams.
