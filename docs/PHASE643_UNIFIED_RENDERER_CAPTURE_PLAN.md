# Phase 643 — unified exact renderer capture-plan handoff

## Playable-slice blocker removed

Phase 641 can prove that one or more exact renderer-owned external sampler
snapshots are absent from the existing historical capture. Phase 642 can turn
that proof into an executable, stage-selective Wine capture. Before Phase 643,
the unified vertical-slice bootstrap stopped between those two contracts and the
user still had to invoke the Phase 642 planner manually.

Phase 643 removes that manual handoff:

```text
bootstrap_native_vertical_slice.py
  -> renderer source bootstrap
  -> Phase 641 renderer native-scene handoff
       |
       +-- scene_set_ready=true ------------------------------> profile path
       |
       `-- exact capture_observation_required=true
             -> Phase 642 build_capture_plan()
             -> external_sampler_capture_plan.json
             -> run_phase641_snapshot_capture_wine.sh
```

The bootstrap still does not launch the retail executable. It only emits the
exact capture artifact when Phase 641 has already proved that such an
observation is required.

## Unified artifact

When actionable Phase 641 evidence exists, the normal vertical-slice output now
contains:

```text
<output>/renderer-native-scene/external_sampler_capture_plan.json
```

with format:

```text
SHIFT.Phase641ExternalSamplerCapturePlan/1
```

The same object is recorded under:

```text
stages.renderer_external_sampler_capture_plan
artifacts.renderer_external_sampler_capture_plan
renderer_capture_observation_required = true
renderer_capture_plan_ready = true
```

The existing Phase 642 Wine wrapper can consume the authoritative scene handoff
from the same output directory and uses the plan semantics to restrict capture
to the exact proven D3D9 sampler stages.

## Admission rule

`bootstrap_native_vertical_slice.py` invokes the Phase 642 planner only when the
Phase 641 handoff itself contains:

```text
boundary.capture_observation_required == true
```

A scene blocker caused by shader ambiguity, scene-instance ambiguity, path
resolution, missing static evidence, or any other non-capture reason never
becomes an inferred recapture request.

If Phase 641 declares capture required but its typed frontier is internally
inconsistent, the Phase 642 planner remains fail-closed. The unified bootstrap:

- does not write an executable capture plan;
- keeps `renderer_capture_plan_ready=false`;
- surfaces the exact `renderer-capture-plan:*` blocker;
- leaves the renderer-native-scene gate blocked.

## Stale artifact policy

A previous `external_sampler_capture_plan.json` is removed when the current run
has no ready exact capture plan. This prevents an earlier observation request
from being mistaken for the current Silverstone/BMW frontier after upstream
evidence changes.

## Process ownership

Phase 643 remains Process 3 coordination only.

It does not:

- run SHIFT;
- change D3D9 proxy behavior;
- derive sampler registers or resource types;
- choose a renderer permutation;
- synthesize renderer-owned textures;
- change native physics scheduling;
- change Process 1 BODY0 proof semantics;
- bypass the Phase 711 retail archive identity gate.

The bootstrap explicitly records:

```text
boundary.generic_renderer_recapture_inferred = false
boundary.renderer_capture_execution_claimed = false
```

Phase 711 continues to own downstream preservation/revalidation of the existing
Process 3 retail archive admission. Phase 643 only shortens the renderer evidence
feedback edge before `scene_set_ready`.

## Regression coverage

`tests/test_phase643_unified_external_sampler_capture_plan.py` verifies that:

1. an exact actionable Phase 641 frontier automatically materializes the Phase
   642 capture plan and records it in the unified bootstrap;
2. a non-capture scene blocker never invokes the planner and removes a stale
   capture-plan artifact;
3. an inconsistent Phase 641 requirement count is rejected and cannot produce
   an executable plan.

The repository-wide CI continues to exercise this together with the Phase 711
runtime identity propagation and the full Linux/Vulkan native runtime smoke.
