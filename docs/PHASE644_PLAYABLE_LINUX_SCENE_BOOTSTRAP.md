# Phase 644 — one-command playable Linux scene bootstrap

## Playable-slice blocker reduced

Phase 643 proved that an already-prepared Silverstone `SHIFT.NativeSceneVulkanSet/1`
and the canonical BMW M3 body can coexist in one neutral scene-set without
changing the native runtime ABI.  Its remaining orchestration gap was manual:
Phase 643 still required the caller to provide a ready BMW material-slice set and
explicit source BFF paths.

Phase 644 removes that handoff for the current playable target:

```text
same retail corpus inputs
  -> existing offline resource/bootstrap
  -> existing Phase 641 prepared Silverstone scene-set
  -> exact canonical BMW/renderer BFF selection from the same corpus
  -> Phase 533 complete BMW body material admission
  -> Phase 643 Silverstone + BMW neutral composition
  -> normal runtime requirements/profile
  -> optional launcher validation
```

No original game execution and no new runtime capture are introduced.

## New corpus bootstrap

`src/scene/native_playable_scene_bootstrap.py` emits:

```text
SHIFT.NativePlayableSceneBootstrap/1
```

It reuses `offline_resource_pipeline.materialize_bff_inputs()` and therefore
accepts the same `.bff`, `.zip`, and directory corpus shapes already supported by
the offline resource pipeline.

For the currently supported vehicle target it requires exactly one archive with
each canonical basename:

```text
BMW_M3_E36.bff
BMW_M3_E36_Cockpit.bff
RENDER.bff
```

Selection is by exact case-insensitive basename only.  Archive order, ZIP member
order, fuzzy names and first-match fallback are not evidence.  Missing or
multiple matching archives block the stage.

The temporary extracted BFF paths are used only while the corpus materialization
context is alive.  User-visible output records source ZIP/directory provenance,
not temporary-path identity.

## Vehicle render materialization

The selected archives feed the existing Phase 533
`build_bmw_body_material_admission()` path:

```text
BMW_M3_E36.bff
+ BMW_M3_E36_Cockpit.bff
+ RENDER.bff
+ canonical BMW body golden manifest
-> SHIFT.BMWBodyMaterialAdmission/1
-> complete SHIFT.BMWMaterialSliceSet/1
```

All selected canonical body primitives must be ready.  Partial material admission
is preserved diagnostically but cannot seed the playable scene.

Phase 644 deliberately does not ask Phase 533 to build the historical
BMW-specific Vulkan bundle set.  The complete material-slice set is instead fed
to Phase 643, which rebuilds genuine neutral `SHIFT.VulkanDrawBundle/1` vehicle
children and preserves the normal `--scene-set` native ABI.

## Playable entry point

New command:

```text
tools/bootstrap_playable_linux_slice.py
```

It accepts the existing `tools/bootstrap_native_vertical_slice.py` arguments.
The current playable command requires the existing renderer-capture evidence path
because the Silverstone side still comes from the Phase 639-641 renderer chain.
It rejects an explicit `--scene-set`: this command owns the generated composite
scene and must not silently replace it with an unrelated prepared scene.

Example shape:

```bash
python tools/bootstrap_playable_linux_slice.py \
  Vehicles.zip Silverstone_Era3_.zip SHIFT_tail.zip \
  -o out/playable-bootstrap \
  --track Silverstone_Era3_GrandPrix \
  --vehicle BMW_M3_E36 \
  --workspace-root . \
  --renderer-capture-jsonl shift_d3d9_capture.jsonl \
  --renderer-pe-evidence out/shift_pe_evidence.json \
  --keyboard
```

The command first runs the merged resource/renderer bootstrap unchanged.  Launch
plan validation is deferred until after Phase 644, because a launch plan created
against the intermediate track-only scene would be the wrong authority for the
playable slice.

## Profile refresh policy

After successful Phase 644 composition, the generated composite scene-set is run
through the same `runtime_input_validation` scene-set validator used for explicit
runtime inputs.  Runtime requirements and the vertical-slice profile are then
rebuilt with the composite path.

This is intentionally conservative: the generated scene is already source-backed
by Phase 533/643, but revalidating it at the launcher boundary cannot strengthen
an unsupported claim and catches filesystem/manifest drift before profile use.

If Phase 644 fails, the playable entry point:

- reports `playable_scene_ready = false`;
- marks the top-level bootstrap not ready;
- clears the old track-only profile artifact;
- clears any old launch plan;
- never validates or launches the track-only scene as the playable result.

## Process 1 BODY0 sync

Process 1 PR #1188 now proves the BMW main/chassis BODY semantically from exact
retail constraint topology:

```text
main_chassis_BODY_selected = true
main_chassis_BODY_index = 0
```

BODY 0 (`body`) is the unique BODY incident to all twenty suspension BAR records
across all four spindle families.  The proof does not rely on the plausibility of
the BODY name.

That result deliberately stops before positive Phase 698/700 admission.  The
remaining direct identity gate is:

```text
*record+0x340 update child
  -> FUN_007615c0 vehicle solver base continuity
```

Until this continuity is proven, Process 1 still reports:

```text
vehicle_BODY_selection_ready = false
phase698_positive_selection_admissible = false
```

Phase 644 therefore records a durable renderer-side vehicle identity but does not
consume BODY 0 as a runtime vehicle pose source.

## Preserved proof boundaries

Phase 644 does **not** consume or claim:

- Process 1 `*record+0x340 -> FUN_007615c0` vehicle-base continuity;
- Phase 698 positive BODY selection;
- Phase 700 runtime BODY pose handoff;
- BODY origin/basis -> renderer matrix convention;
- a dynamic vehicle world transform;
- a camera-follow target;
- Process 2 Phase 701 provider cadence ownership.

The BMW children still carry the source RenderCommand world transform serialized
through the existing SVWT path.  That transform is a resource/render bootstrap
transform, not persistent physics pose transport.

The durable benefit is object identity: the composite scene now contains an
explicit `source_group=vehicle` subgroup with canonical BMW mesh/material identity.
The renderer target therefore no longer needs to be rediscovered when the
remaining Process 1 continuity proof permits Process 2 to emit the proven BODY 0
pose.

## Regression coverage

`tests/test_native_playable_scene_bootstrap.py` verifies:

- exact canonical archive selection;
- Phase 533 -> Phase 643 handoff;
- no manual material-slice/BFF path requirement;
- missing `RENDER.bff` rejection;
- duplicate canonical basename rejection;
- unsupported vehicle rejection before corpus parsing.

`tests/test_bootstrap_playable_linux_slice.py` verifies:

- launcher validation is deferred until after composition;
- the same original corpus inputs feed Phase 644;
- requirements/profile are rebuilt with the generated composite scene;
- the generated scene reaches the final launch plan;
- a blocked Phase 644 stage removes stale track-only profile/launch artifacts;
- Phase 700 pose transport remains unconsumed.

## Blocker after Phase 644

Once this phase is ready for the supplied corpus, the render/orchestration chain
for the milestone becomes:

```text
Silverstone resources + existing renderer evidence
+ canonical BMW resources
-> one prepared native scene-set
-> one launch profile
```

The next cross-process blocker is no longer “how do track and vehicle enter one
renderer invocation?” and no longer “which retail BODY is the chassis?”.  The
remaining dynamic join is:

```text
proven chassis BODY 0
+ prove *record+0x340 -> FUN_007615c0 vehicle-base continuity
-> Phase 698/700 selected persistent BODY 0 pose
+ prove BODY origin/basis -> vehicle renderer world-transform convention
+ Phase 643 durable vehicle renderer identity
-> update vehicle subgroup SVWT each simulation step
```

Until those remaining joins are proven, Phase 644 keeps the vehicle render
transform static and fail-closed rather than guessing from BODY name, proximity
or matrix shape.
