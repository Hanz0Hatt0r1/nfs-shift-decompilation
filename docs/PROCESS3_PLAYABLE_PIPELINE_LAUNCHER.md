# Process 3 playable resource-pipeline launcher

`tools/run_native_vertical_slice_playable_pipeline.py` is a narrow consumer for a
future one-command playable path. It does not weaken the existing resource-pipeline
single-authority rule in `tools/run_native_vertical_slice.py`.

The wrapper first asks the ordinary launcher to validate the complete profile with
the pipeline's original runtime-proven scene, physics manifest, participant runtime
evidence, camera state, BODY feedback packets, input mode, runtime executable and
retail target gates. It then rebuilds
`SHIFT.ResourcePipelinePlayableSceneJoin/1` from current files and admits the Phase
643 composite scene only when the join proves all of the following:

- the playable bootstrap consumed the exact `pipeline_run.inputs.runtime_proven_scene_set`;
- the source scene manifest SHA-256 still matches the Phase 643 source record;
- the composite scene path matches the Phase 643 composition record;
- the composite `bundle_set_manifest.json` SHA-256 matches current bytes;
- the composite scene remains a ready `SHIFT.NativeSceneVulkanSet/1` with a ready
  prepare report.

Only the already-validated launch plan's `--scene-set` value is replaced. Physics,
participant, camera and BODY feedback paths remain exactly those admitted by the
base launcher.

This contract does not claim runtime execution, dynamic vehicle BODY motion,
provider-present dispatch, or retail-loop equivalence.
