# Phase 641 — exhaust existing capture scene snapshots before recapture

## Blocker removed

Phase 640 closes the regenerated renderer-evidence -> prepared native-scene
handoff when all Phase 580/585 renderer resources are already available.
However, it still accepts Phase 589/592 external sampler snapshot manifests as
manual inputs even though the repository already contains the machinery to
build them from the same historical capture:

```text
Phase 630 attributed draw-local observations
+ Phase 578 runtime-proven scene bundle
+ Phase 576 scene bridge
+ existing captured PPM files
-> Phase 591 repeated-instance transform match
-> Phase 590/592 external sampler snapshots
-> Phase 580 Vulkan scene set
-> Phase 585 prepared scene set
```

Phase 641 makes that existing-capture completion automatic and therefore moves
the recapture decision later, behind the actual PPM/observation diagnostics.

## Implementation

Wrapper:

```text
tools/materialize_renderer_native_scene_capture_handoff.py
```

It first executes the unchanged Phase 640 handoff. It retries only when Phase
640 reached a Phase 580 or Phase 585 blocker. Any earlier blocker from shader
attribution, static scene identity, runtime RenderBinding provenance, or
NativeSceneBundle construction stops the wrapper immediately.

The unified `tools/bootstrap_native_vertical_slice.py` uses this wrapper and
accepts:

```text
--renderer-capture-root DIR
```

When omitted, the filesystem directory containing
`--renderer-capture-jsonl` is used as the capture root. For captures created by
`tools/run_shift_capture.ps1`, this is the exact launcher `OutputDir`: the JSONL
lives directly under that directory and texture snapshots live under its
`textures/` child. The root is location/provenance context only; it is never
resource or scene identity evidence.

## Phase 591 integration

For a runtime-proven scene bundle with repeated bindings, Phase 641 runs the
existing `build_scene_instance_transform_match()` contract.

The match still requires exact IEEE-754 float32 equality between a scene world
matrix and one contiguous four-register draw-local VS constant window. Both
row-major and transpose layouts are checked, but no retail register semantic is
assigned.

A blocked Phase 591 report is retained as diagnostics. It becomes a top-level
blocker only when Phase 590 actually needs that repeated binding to resolve an
external sampler.

## Phase 590/592 integration

The existing `build_scene_external_sampler_capture_adapter()` consumes:

- ready `SHIFT.NativeSceneBundle/1`;
- ready `SHIFT.SGBRenderBindingBridge/1`;
- the exact regenerated `SHIFT.IMBRuntimeCapturePipeline/1`;
- the capture root;
- the Phase 591 transform match.

It preserves the existing requirements:

- strong Phase 572 shader attribution;
- exact binding/draw identity;
- observed D3D9 texture creation;
- exact sampler register/type;
- one captured PPM for external sampler2D;
- six named captured PPM faces for the proven samplerCube s3 path;
- exact snapshot provenance under the explicit capture root.

Cross-platform relocation is fail-closed and producer-backed. Native
Windows-absolute paths are portable only through the exact layout established by
`tools/run_shift_capture.ps1`:

```text
<OutputDir>/shift_d3d9_capture.jsonl
<OutputDir>/textures/<captured PPM>
```

A recorded absolute `...\\textures\\<file>` therefore maps deterministically to
`capture_root/textures/<file>`. Phase 590 never recursively searches the root by
basename and never treats a unique basename as identity proof. A non-launcher
source parent reports `snapshot-path-no-exact-relocation`; a missing file in the
launcher layout reports `snapshot-path-launcher-layout-not-found`. Exact relative
paths continue to resolve only at their recorded relative location.

These are specific missing observations/artifacts, not generic requests for a
new capture.

## Exact missing-snapshot frontier

A Phase 590 `capture-observation-count:0` is not sufficient evidence that a new
snapshot capture is required. Phase 590 filters its candidates to already
captured PPM content, so the same count can mean several different things.

Phase 641 now rechecks the compact Phase 573 draw-local observations only after
Phase 590 has identified the exact runtime-admitted scene sampler. It emits an
entry under:

```text
existing_capture_completion.runtime_evidence_required[]
```

only when all of the following are already observed together:

1. exact `binding_index` from the runtime-proven scene draw;
2. exact external sampler register from the RenderBinding submesh;
3. a draw-local active texture binding at that register;
4. observed D3D9 resource creation;
5. the expected resource type (`texture2d` or `cube_texture`);
6. no valid snapshot payload for that typed observation.

Each entry preserves the capture frame/draw indices, register, sampler name/type,
resource type, observed snapshot statuses/path cardinalities and the minimal
`requested_texture_stage`. A 2D sampler requires one PPM path; the proven cube
s3 path requires six face paths.

The handoff boundary then records:

```text
capture_observation_required = true
capture_observation_requirement_count = N
new_capture_required = false
```

The last value deliberately remains false as a global claim: an explicit
already-proven external resource input can still satisfy the renderer boundary.
The new field states only that automatic completion from the supplied capture
cannot proceed without the listed draw-local snapshot observation.

Phase 641 does **not** emit this requirement for a path relocation failure, a
scene-instance ambiguity, an unobserved/mismatched texture creation type, or an
already valid snapshot. Those cases remain their original fail-closed blockers.

## Retry policy

Only a ready Phase 590/592 adapter produces snapshot contracts for the retry.
Phase 641 then reruns the existing Phase 580 and Phase 585 builders in a new
output directory.

The final handoff remains:

```text
SHIFT.RendererNativeSceneHandoff/1
```

and `scene_set_ready=true` still requires a ready Phase 585 prepare report.

If explicit renderer-resource inputs were supplied to Phase 640
(`--renderer-environment-cube-dds`, explicit 2D snapshot manifest, or explicit
cube snapshot manifest), those inputs remain authoritative and Phase 641 does
not mix them with capture-derived resources.

## Diagnostics

A Phase 641-completed handoff records:

- `native_scene_instance_transform_match.json`;
- `native_scene_external_sampler_capture.json`;
- generated Phase 589 snapshot contract when applicable;
- generated Phase 592 cube snapshot contract when applicable;
- retried `NativeSceneVulkanSet` directory;
- retried Phase 585 prepare report;
- exact Phase 591/590 diagnostics under `existing_capture_completion`;
- exact per-stage missing snapshot observations under
  `existing_capture_completion.runtime_evidence_required` when and only when
  the typed draw-local resource was already observed without usable content.

The top-level vertical-slice report also records the effective
`renderer_capture_root`.

## Non-claims

Phase 641 does not claim that:

- capture-root path proximity proves resource identity;
- basename uniqueness proves snapshot identity;
- a non-launcher directory suffix may be remapped heuristically;
- VS constant position proves retail world-matrix register semantics;
- a blocked repeated instance may be selected manually;
- renderer-owned textures may be synthesized;
- Phase 590 observation absence automatically requires recapture;
- a zero snapshot candidate count proves a texture binding existed;
- a new capture is globally required when an explicit proven resource could be supplied.

## Regression coverage

Tests prove that:

- Phase 591 and Phase 590 execute before the Phase 580/585 retry;
- exact generated snapshot contracts are passed to Phase 580;
- a ready Phase 585 retry is required before scene readiness;
- exact `run_shift_capture.ps1` `textures/` relocation remains portable across
  Windows/Linux;
- a unique basename outside that exact producer layout is rejected;
- Phase 590 path/instance blockers are preserved without a recapture claim;
- an observed typed sampler2D binding with no PPM produces one exact stage
  observation requirement;
- an already captured valid PPM does not produce that requirement;
- a resource-type mismatch cannot be promoted into a capture requirement;
- an incomplete samplerCube s3 snapshot requires exactly six face paths;
- an earlier Phase 576 blocker is never bypassed;
- explicit Phase 640 renderer-resource inputs remain authoritative.
