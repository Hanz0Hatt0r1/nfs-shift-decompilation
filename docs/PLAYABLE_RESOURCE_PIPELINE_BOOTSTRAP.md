# Playable resource-pipeline bootstrap

`tools/bootstrap_playable_pipeline_slice.py` is the Process 3 one-command path for building a provenance-gated playable native vertical-slice profile from an already prepared offline resource pipeline.

It does **not** execute the native runtime. Its highest authority is a validated launch plan when `--validate-launch-plan` is supplied.

## Preconditions

The selected resource pipeline must already provide:

- a ready `SHIFT.OfflineResourcePipelineRun/1`;
- a ready native resource handoff;
- an exact runtime-proven native scene set;
- the exact native physics manifest recorded by the handoff;
- transported, ready `SHIFT.NativePhysicsParticipantRuntimeEvidence/1` with a proven registry/selector identity join and a ready participant instance;
- target identity compatible with the requested `--track` and `--vehicle` when target metadata is present.

Camera state and BODY-feedback packets are still explicit runtime inputs. The pipeline does not synthesize or replace them.

## Workspace confinement

`--workspace-root` must name an existing directory. `--output` must resolve inside that workspace. These checks run before resource-pipeline validation, BFF materialization, playable scene composition, or output-directory creation.

This means an escaped output such as `../outside` fails with exit code `2` without creating the external directory or touching the resource pipeline.

## Example

```bash
python tools/bootstrap_playable_pipeline_slice.py \
  /path/to/retail/VehicleArchive.bff \
  /path/to/retail/TrackArchive.bff \
  --workspace-root /work/nfs-shift \
  --output /work/nfs-shift/out/playable-pipeline \
  --track Silverstone_Era3_GrandPrix \
  --vehicle BMW_M3_E36 \
  --resource-pipeline out/offline-pipeline \
  --camera-state runtime/camera.json \
  --solver-frame runtime/solver.sbfr \
  --generated-body-constraint-frame runtime/generated.gbcf \
  --constraint-sample-relation-frame runtime/relations.csrf \
  --constraint-relation-reset-frame runtime/reset.crrf \
  --post-solve-projection runtime/post.sbps \
  --keyboard \
  --frames 600 \
  --validate-launch-plan
```

Paths recorded into the generated native profile remain workspace-local. The original BFF/ZIP/directory inputs may be outside the workspace because they are source material, not profile artifacts.

## Pipeline order

The command fails closed through these stages:

1. validate workspace/output confinement;
2. validate resource-pipeline scene, physics, participant evidence, and target identity;
3. build the ordinary offline vertical-slice bootstrap without replacing pipeline scene/physics/participant authority;
4. compose the Phase 643 track + BMW playable scene using the pipeline's exact source scene;
5. prepare a playable resource-pipeline profile while keeping camera/BODY inputs explicit;
6. when requested, rebuild the resource-pipeline-to-composite provenance join from current files and validate the native launch plan.

The final playable launcher submits the derived composite scene only after the provenance join proves it was derived from the pipeline source scene. Physics and participant evidence continue to come from the pipeline handoff.

## Output artifacts

The output directory can contain:

- `playable_pipeline_bootstrap.json` — orchestration report;
- `playable-scene/playable_scene_bootstrap.json` — playable scene bootstrap/provenance input;
- `vertical_slice_profile.json` — generated native runtime profile when profile preparation succeeds;
- `launch_plan.json` — generated only when `--validate-launch-plan` succeeds.

The top-level report status is:

- `blocked` — an admission, materialization, composition, profile, or launch-plan gate failed;
- `profile-ready` — the profile is ready and launch-plan validation was not requested;
- `launch-plan-ready` — the profile and provenance-gated launch plan are ready.

Exit code is `0` only when the requested readiness level is reached; otherwise it is `2`.

## Input modes

Choose exactly one input mode:

- `--input-script PATH` for deterministic scripted input;
- `--interactive` for continuous keyboard/window-driven mode; do not provide `--frames`;
- `--keyboard --frames N` for a bounded keyboard-mode run plan.

`--validate-launch-plan` validates and writes the launch plan but still does not execute it. `--validation` only requests Vulkan validation in that generated plan.

## Evidence boundary

This bootstrap does not claim:

- retail game-loop equivalence;
- runtime execution success;
- new participant identity evidence;
- new S6/physics semantics;
- renderer-resource identity beyond the existing admitted Process 3/renderer contracts;
- that mere path presence is provenance.

The final composite-scene authority comes from `SHIFT.ResourcePipelinePlayableSceneJoin/1`, which rechecks the source scene path, source manifest SHA-256, Phase 643 source record, and composite manifest SHA-256 from the current filesystem state.
