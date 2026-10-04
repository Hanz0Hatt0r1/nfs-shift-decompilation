# Phase 642 — exact Phase 641 external-sampler capture on Wine

## Playable-slice blocker removed

Phase 641 can now prove a very narrow renderer evidence frontier:

```text
runtime-admitted Silverstone scene draw
+ exact binding index
+ exact external sampler register/type
+ observed matching D3D9 texture creation
+ missing/incomplete snapshot content
-> runtime_evidence_required[]
```

Before Phase 642 the Windows PowerShell launcher could enable selective texture
snapshots, but the Linux/Wine launcher had no direct Phase 641 handoff path.
That left a manual gap precisely where the first playable Linux slice needs the
remaining renderer-owned resources.

Phase 642 closes that gap without adding any new renderer or D3D9 inference.

## Components

Planner:

```text
tools/phase641_external_sampler_capture_plan.py
```

Wine wrapper:

```text
tools/run_phase641_snapshot_capture_wine.sh
```

The planner consumes the existing final handoff format:

```text
SHIFT.RendererNativeSceneHandoff/1
```

and reads only:

```text
boundary.capture_observation_required
boundary.capture_observation_requirement_count
existing_capture_completion.runtime_evidence_required[]
```

It emits:

```text
SHIFT.Phase641ExternalSamplerCapturePlan/1
```

with a sorted, deduplicated `texture_stage_list` and comma-separated
`texture_stages` string suitable for the native D3D9 proxy.

## Fail-closed validation

Every actionable requirement must already contain the exact Phase 641 facts:

- non-negative `binding_index`;
- sampler register in `s0..s15`;
- `requested_texture_stage` equal to that register;
- `sampler2D` paired only with observed `texture2d` and one required snapshot;
- `samplerCube` paired only with observed `cube_texture` and six required faces;
- reason equal to `snapshot-content-not-captured` or
  `snapshot-content-incomplete`.

Any mismatch blocks the plan. Phase 642 never converts a generic
`capture-observation-count:0` into a recapture request and never guesses a
sampler register from shader/material conventions.

If Phase 641 has no exact `runtime_evidence_required` rows, the planner reports
`status=not-needed` and the Wine wrapper refuses to start a capture.

## Wine capture path

The wrapper derives the exact stage set from the planner and reuses the already
implemented native proxy controls:

```text
SHIFT_D3D9_CAPTURE_TEXTURE_SNAPSHOT=1
SHIFT_D3D9_CAPTURE_TEXTURE_STAGES=<exact Phase 641 stages>
SHIFT_D3D9_CAPTURE_TEXTURE_SNAPSHOT_DIR=Z:\...\<OutputDir>\textures
```

It forces `--mode capture`, because `SetTexture` snapshot emission is behind the
proxy's capture-render-event gate. An explicit `--mode diagnostic` or
`--mode passthrough` is rejected instead of silently producing a capture with no
snapshot evidence.

The wrapper also deletes `<OutputDir>/textures` before each run so stale PPMs
from an older process cannot satisfy path existence accidentally. The ordinary
Wine launcher remains responsible for proxy/backend staging, Wine-prefix
selection, trigger/frame controls, D3DX staging, crash recovery, and game
arguments.

Capture mode is inserted before every forwarded argument, including a later
`--` game-argument separator, so it cannot be reordered into SHIFT's own command
line.

## Example

After a Phase 641 handoff reports `capture_observation_required=true`:

```bash
python3 tools/phase641_external_sampler_capture_plan.py \
  out/vertical-slice/renderer_native_scene_handoff.json \
  --output out/vertical-slice/external_sampler_capture_plan.json
```

The exact Wine capture can then be launched with:

```bash
bash tools/run_phase641_snapshot_capture_wine.sh \
  --handoff out/vertical-slice/renderer_native_scene_handoff.json \
  --game /path/to/SHIFT.exe \
  --proxy /path/to/d3d9.dll \
  --output out/phase642-capture
```

Existing `run_shift_capture_wine.sh` options such as `--trigger`,
`--resource-trigger`, `--pre-frames`, `--post-frames`, `--wine`, or game
arguments after `--` may be forwarded unchanged.

## Proof boundary

Phase 642 does **not** claim that:

- a new capture is always required;
- an absent snapshot proves which sampler was bound;
- a stage alone proves resource identity;
- a captured PPM identifies a scene draw without the Phase 641 join;
- material textures may substitute for renderer-owned external samplers;
- the Wine wrapper changes native scene admission semantics.

The output remains capture evidence only. It must be fed back through the
existing Phase 630 -> Phase 641 -> Phase 590/592 -> Phase 580/585 chain before
`scene_set_ready` can become true.

## Regression coverage

`tests/test_phase642_wine_external_sampler_snapshot_capture.py` freezes:

- exact stage sorting/deduplication;
- register/stage equality;
- sampler/resource-type equality;
- not-needed behavior when Phase 641 has no exact capture frontier;
- machine-readable stage output;
- shell syntax;
- stale snapshot cleanup;
- capture mode ordering before game arguments;
- reuse of the existing native proxy snapshot environment variables.
