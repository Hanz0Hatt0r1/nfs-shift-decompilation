# Phase 640 — regenerated renderer evidence to prepared native scene

## Blocker removed

The Process 3 one-command vertical-slice bootstrap could already build the exact
resource/static-scene side and regenerate the Silverstone renderer frontier from
the historical D3D9 capture.  The remaining manual gap was the reverse handoff:

```text
regenerated Phase 630 runtime attribution
-> manual Phase 574 admission JSON
-> manual scene bridge
-> manual NativeSceneBundle
-> manual NativeSceneVulkanSet
-> manual Phase 585 prepare
-> manually supplied scene_set in the vertical-slice profile
```

Phase 640 connects those existing contracts without adding new renderer proof
semantics.

## Contract

New orchestration report:

```text
SHIFT.RendererNativeSceneHandoff/1
```

implemented by:

```text
tools/materialize_renderer_native_scene_handoff.py
```

The source inputs are:

- the exact `SHIFT.OfflineRuntimeBootstrap/1` produced by the current resource
  bootstrap invocation;
- the exact `SHIFT.SilverstoneRendererSourceBootstrapProductionRun/1` produced
  by the current renderer invocation.

The handoff then reuses the existing chain:

```text
Phase 630 compact Phase 572 rows
-> Phase 574 IMBRuntimeShaderAdmission
-> Phase 576 runtime RenderBinding join
-> Phase 577 RuntimeProvenDraw provenance
-> Phase 578 NativeSceneBundle
-> Phase 580 NativeSceneVulkanSet
-> Phase 585 NativeSceneVulkanSetPrepare
```

`scene_set_ready=true` is emitted only after the Phase 585 prepare report is
ready.

## Phase 630 transport boundary

`SHIFT.IMBRuntimeCapturePipeline/1` stores its exact per-resource rows under
`resource_results[]`.  For each row it already preserves:

- exact IMB resource path;
- exact IMB SHA-256;
- routed binding indices;
- the filtered Phase 572 `candidate_binding_results[]` objects.

Phase 640 reconstructs only the missing outer
`SHIFT.IMBRuntimeShaderVariantMatch/1` envelope required by Phase 574.  The
candidate result objects are JSON-copied without changing their fields or
re-running shader attribution.

A binding result outside the routed binding set is rejected.  No candidate is
selected by filename, archive order, ranking, or frequency.

## Static-scene input boundary

The runtime bootstrap supplies the selected static scene build and scene IR.
Before Phase 576 runs, Phase 640:

- requires the offline bootstrap to be ready;
- resolves the persisted SGB render-binding admission artifact;
- rechecks its recorded SHA-256;
- requires the static scene build to be resource-ready;
- requires the scene IR manifest to exist.

A hash mismatch stops before runtime shader admission is applied to the scene.

## Partial shader admission

Phase 574 may be `partial` while still containing exact admitted bindings.
Phase 640 permits those admitted bindings to continue because downstream Phase
577/578 contracts already exclude every submesh lacking
`SHIFT.RuntimeProvenDraw/1` provenance.

This does **not** mean a unique static shader is runtime proof.  The chain still
requires the original Phase 572 attributed result for every promoted draw.

## Runtime requirements refresh

`build_runtime_requirements()` now accepts an optional ready
`SHIFT.RendererNativeSceneHandoff/1`.

Only when both:

```text
ready = true
scene_set_ready = true
```

are present does the `scene_set` runtime requirement become satisfied, with the
prepared scene-set directory recorded as its artifact.

`tools/bootstrap_native_vertical_slice.py` now performs this automatically when
renderer evidence is requested and no explicit `--scene-set` was supplied:

```text
retail resources
-> OfflineRuntimeBootstrap
-> regenerated renderer evidence
-> RendererNativeSceneHandoff
-> refreshed runtime requirements
-> refreshed vertical-slice profile
```

An explicitly supplied scene set remains authoritative and suppresses automatic
scene materialization, avoiding replacement of already-proven external input.

## Renderer-owned resources remain fail-closed

Phase 580 may still block on an external sampler or environment cube.  Phase 640
accepts optional already-proven inputs:

```text
--renderer-environment-cube-dds
--renderer-external-sampler-snapshots
--renderer-external-sampler-cube-snapshots
```

It never invents a renderer-owned texture and never converts a Phase 580 blocker
into a generic recapture request.  If an external sampler remains unresolved,
the unified report is:

```text
status = renderer-native-scene-blocked
renderer_evidence_ready = true
renderer_native_scene_ready = false
```

with the exact downstream blocker preserved.

## Non-claims

Phase 640 does not claim that:

- Phase 574 shader admission is draw admission;
- static resource uniqueness is runtime identity;
- one surviving renderer candidate is portable resource identity;
- missing external sampler state may be synthesized;
- renderer evidence readiness alone means Vulkan scene readiness;
- the original game must be launched again;
- a new capture is required merely because Phase 580/585 remains blocked.

## Tests

Regression coverage includes:

- Phase 630 `resource_results[]` transport into Phase 574 without mutation;
- rejection of a transported result outside its routed binding set;
- static scene artifact SHA mismatch stopping before Phase 574;
- partial Phase 574 admission flowing only through existing provenance gates;
- Phase 585 as the final `scene_set_ready` gate;
- runtime requirements accepting only a ready Phase 640 handoff;
- top-level one-command resource -> renderer -> native scene orchestration;
- explicit scene-set authority;
- unresolved external sampler blockers remaining explicit and offline-first.
