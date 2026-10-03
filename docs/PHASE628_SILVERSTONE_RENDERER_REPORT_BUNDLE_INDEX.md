# Phase 628 — Silverstone renderer report bundle index

Phase 628 removes the manual unzip/filename handoff between historical renderer
artifacts such as `out.zip` and the Phase 627 Silverstone production runner.
It is an **artifact indexing step only** and adds no renderer proof semantics.

## Tool

`tools/index_silverstone_renderer_report_bundle.py` scans one or more ZIP handoff
bundles and identifies reports only by their embedded `format` field.

Recognized Phase 627 inputs are:

| Runner key | Embedded format | Required in bundle |
| --- | --- | --- |
| `base_audit` | `SHIFT.D3D9RendererRequirementAudit/1` | yes |
| `ambiguity_audit` | `SHIFT.IMBDrawLocalAmbiguityAudit/1` | yes |
| `draw_local` | `SHIFT.D3D9TargetDrawLocalEvidence/1` | yes |
| `capture_pipeline` | `SHIFT.IMBRuntimeCapturePipeline/1` | yes |
| `object_candidate_join` | `SHIFT.SGBRuntimeObjectCandidateJoin/1` | no; required later only if Phase 624 finds repeated placements |
| `runtime_shader_targets` | `SHIFT.IMBRuntimeShaderTargetSet/1` | no; Phase 627 already has a committed Silverstone target-set default |

The ZIP entry name is diagnostic provenance only. It is never a selection key.

## Exact duplicate policy

For every recognized format the indexer computes:

- raw ZIP-entry SHA-256;
- canonical JSON SHA-256 using recursively serialized sorted JSON keys;
- source bundle SHA-256;
- ZIP entry path and uncompressed size.

When one format occurs more than once:

- if all occurrences have the same canonical JSON SHA-256, they are treated as
  one report content identity and **all** source occurrences are retained;
- if more than one canonical payload exists, the format becomes
  `ambiguous-distinct-payloads` and no normalized report is emitted.

No occurrence is selected by filename, archive order, newest timestamp,
frequency, or apparent completeness.

## Output

The output directory receives normalized filenames only for unambiguous report
content identities plus:

- `silverstone_renderer_report_bundle_index.json`
  (`SHIFT.SilverstoneRendererReportBundleIndex/1`).

The index records:

- source bundle size/SHA-256;
- every recognized occurrence and both raw/canonical hashes;
- missing required formats;
- ambiguous formats;
- skipped oversized JSON entries;
- normalized output paths;
- the exact Phase 627 argument paths that were recovered.

Normalized JSON is written atomically.

## Usage with the existing `out.zip`

```bash
python tools/index_silverstone_renderer_report_bundle.py \
  out.zip \
  --output-dir out/silverstone_renderer_inputs
```

Inspect:

```text
out/silverstone_renderer_inputs/silverstone_renderer_report_bundle_index.json
```

If the index is `ready`, feed the normalized reports into Phase 627. For
example:

```bash
python tools/run_silverstone_renderer_production.py \
  --output-dir out/silverstone_renderer_production \
  --base-audit out/silverstone_renderer_inputs/d3d9_renderer_requirement_audit.json \
  --ambiguity-audit out/silverstone_renderer_inputs/silverstone_d3d9_draw_local_ambiguity_audit.json \
  --draw-local out/silverstone_renderer_inputs/d3d9_target_draw_local_evidence.json \
  --capture-pipeline out/silverstone_renderer_inputs/silverstone_imb_runtime_capture_pipeline.json \
  --object-candidate-join out/silverstone_renderer_inputs/silverstone_sgb_runtime_object_candidate_join.json \
  --corpus Silverstone_Era3_.zip \
  --corpus SHIFT_tail.zip
```

Omit `--object-candidate-join` when the index did not contain that optional
format. Phase 627 will require it only if the exact Phase 624 result proves that
repeated scene placements remain.

The committed
`evidence/silverstone_era3_runtime_shader_targets.json` remains the Phase 627
default when the handoff ZIP does not contain a runtime target-set report.

## Large JSON safety boundary

Individual JSON entries larger than 128 MiB are skipped before decompression by
default. The limit can be changed with `--max-json-bytes`. A required report
that is skipped remains a missing-input blocker; the tool does not silently
raise the limit or substitute a similarly named file.

This is especially important because raw capture logs may be much larger than
the compact derived reports. Phase 628 is not a raw-capture parser and does not
need to ingest `shift_d3d9_capture.jsonl`.

## Capture policy

Phase 628 cannot create a new-capture requirement. Its blockers are artifact
handoff blockers only. In particular, it does not reinterpret the known
historical absence of:

- `SetSamplerState` events;
- VB/IB `buffer_payload` snapshots;
- portable texture path+SHA events;
- texture payload snapshots.

Those observations remain under the existing Phase 621/626 conditional frontier
rules.

## Regression coverage

`tests/test_index_silverstone_renderer_report_bundle.py` covers:

- exact format-based extraction independent of entry filenames;
- content-equivalent duplicate reports across multiple bundles;
- distinct payload ambiguity for one embedded format;
- optional report absence;
- required report absence;
- oversized JSON skipping;
- invalid ZIP fail-closed behavior with a persisted index manifest.
