# Phase 600 — raw D3D9 capture capability audit

## Goal

Turn an arbitrary native D3D9 JSONL capture into a compact, streaming
capability report before expensive Silverstone attribution is attempted.

This is motivated by the production capture supplied for the project. That
capture is large enough that manually inspecting isolated JSONL records does
not reliably answer which later evidence gates can actually be exercised.

## Contract

`SHIFT.D3D9RawCaptureAudit/1` reports:

- event counts and capture frame/event/tick bounds;
- unique VS/PS byte-hash counts;
- optional overlap with the Phase 568 Silverstone pixel-shader target
  inventory;
- exact resource path/SHA metadata presence;
- buffer/texture payload presence;
- captured 2D texture snapshots;
- captured six-face cube snapshots;
- duplicate JSON object keys before ordinary JSON parsing collapses them.

The audit is line-streaming and does not retain capture events.

## Capability flags

The report exposes deliberately narrow input-readiness flags:

- `phase569_shader_prefilter_input`;
- `programmable_draw_state_observed`;
- `exact_resource_identity_observed`;
- `buffer_payload_input_observed`;
- `phase590_sampler2d_snapshot_input`;
- `phase593_sampler_cube_snapshot_input`;
- `phase598_raw_input_candidate`.

These flags describe whether the raw capture contains the corresponding input
class. They do not claim that a later attribution/admission contract succeeds.

In particular, `phase598_raw_input_candidate` still does not replace the
Phase 595 candidate join, Phase 596 root consensus, Phase 597 root application
or Phase 598 coverage gates.

## Usage

```bash
python src/graphics/d3d9/d3d9_raw_capture_audit.py \
  shift_d3d9_capture.jsonl \
  out/d3d9_capture_audit.json \
  --target-inventory evidence/silverstone_era3_runtime_shader_targets.json
```

The Phase 568 evidence JSON is accepted directly through its
`families[].pixel_shader_sha256` inventory. A full
`SHIFT.IMBRuntimeShaderTargetSet/1` with `unique_targets` is also accepted.

CLI input paths are cwd-relative when they already exist. Otherwise, relative
capture and `--target-inventory` paths are retried from the repository root, so
the script may be launched by absolute path from outside the checkout.

## Current supplied capture

Manual inspection of the supplied capture established the key missing input
classes that motivated this contract:

- shader bytecode, shader bindings, constants and indexed draws are present;
- four `CreateCubeTexture` events are present;
- no `buffer_payload` events were observed;
- no `texture_payload` events were observed;
- no captured `snapshot_paths` were observed;
- no `resource_path` / `resource_sha256` runtime identity metadata was
  observed.

Therefore the supplied file is already useful for Phase 569-style shader/draw
analysis and render-state reconstruction, but it cannot by itself provide the
snapshot/resource-identity evidence required to close Phases 590, 593 or the
full Phase 598 attribution path.

The executable audit is the authoritative way to reproduce that classification
on future captures.
