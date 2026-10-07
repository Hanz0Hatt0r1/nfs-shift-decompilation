# Offline native resource handoff

Process D has a fail-closed bridge from the offline BFF catalog/bootstrap to the
native runtime's existing render and physics resource inputs.  It can also carry
an already-proven participant runtime-identity artifact without creating or
inferring that evidence itself.

Implemented in:

- `src/resources/offline_native_resource_handoff.py`;
- `src/resources/offline_native_participant_handoff.py`;
- `tools/shift_resource_pipeline.py native-handoff` / `all`;
- `tools/run_native_vertical_slice.py` resource-pipeline profile mode.

The bridge does **not** create runtime evidence and does not replace any renderer,
physics, participant, camera, BODY-feedback, or retail-identity provenance gate.

## Physics side

`SHIFT.VehiclePhysicsResourceManifest/1` is generated directly from:

1. `SHIFT.OfflineResourceCatalog/1`;
2. `SHIFT.SceneVehicleBootstrap/1`;
3. `SHIFT.VehiclePhysicsBundleExtractor/1` / `SHIFT.VehiclePhysicsAssetGraph/1`.

For CDF/EDF/GDF/SDF/TBF/BBF the join requires the exact selected vehicle archive,
resource id, logical path, entry index, compression type, compressed size and
uncompressed size. Decoded/raw SHA-256 comes from the actual bundle extraction.
CDF/EDF/GDF/SDF decoded SHA-256 must also agree with the physics asset graph.

For the currently supported native BMW vertical slice, the bridge additionally
writes `native_physics_manifest.json` using the existing
`SHIFT.BMWM3VehiclePhysicsResourceManifest/1` contract. It is generated only
when the selected archive is exactly `BMW_M3_E36.bff`; other vehicles remain
explicitly blocked at the current native-runtime compatibility boundary rather
than being relabeled as BMW.

This removes the need to hand-author the BMW physics resource manifest for a new
offline pipeline run.

## Scene side

The bridge accepts an already existing runtime-proven
`SHIFT.NativeSceneVulkanSet/1` directory. It does not synthesize one from static
resources.

Every ready scene draw must join to exactly one catalog IMB using:

- selected track visual archive identity;
- exact normalized resource path;
- exact decoded payload SHA-256.

The accompanying `SHIFT.NativeSceneVulkanSetPrepare/1` is loaded from the same
directory. The file-level command also verifies that its recorded source manifest
SHA-256 matches the actual `bundle_set_manifest.json` bytes.

Therefore static BFF presence cannot promote an unproven scene draw, shader
permutation, instance, transform or external sampler into the native scene.

## Participant runtime-identity transport

The handoff may optionally receive an existing
`SHIFT.NativePhysicsParticipantRuntimeEvidence/1` through
`--participant-runtime-evidence`.

The transport accepts the artifact only when all existing participant-evidence
readiness fields are already proven:

- `format == SHIFT.NativePhysicsParticipantRuntimeEvidence/1`;
- `version == 1`;
- `ready == true`;
- `registry_selector_identity_join_proven == true`;
- `participant_instance_ready == true`;
- no participant blocking reasons are present.

Accepted bytes are copied unchanged to:

```text
native-handoff/native_physics_participant_runtime_evidence.json
```

The handoff records both source and copied SHA-256 and requires byte equality.
An invalid retry removes a stale copied artifact instead of leaving an earlier
ready file behind.

Participant readiness remains a separate axis:

```text
participant_runtime_identity_evaluated
participant_runtime_identity_ready
participant_runtime_identity_blocking_reasons
```

It does not change `resource_inputs_ready` or the existing scene/physics handoff
`ready` result. `--require-participant-runtime-identity` changes only the command
exit gate. The transport never creates a participant observation, does not
reinterpret the pointer token, and does not dereference it.

## Commands

After `tools/shift_resource_pipeline.py all` has produced the resource outputs,
the standalone handoff can be rebuilt without re-decoding the BFF corpus:

```bash
python tools/shift_resource_pipeline.py native-handoff \
  out/offline-pipeline/resource_catalog.json \
  out/offline-pipeline/scene_vehicle_bootstrap.json \
  out/offline-pipeline/vehicle_physics_bundle_report.json \
  --scene-set out/native-scene-vulkan \
  --participant-runtime-evidence out/native_physics_participant_runtime_evidence.json \
  --require-participant-runtime-identity \
  -o out/offline-pipeline/native-handoff
```

The preferred one-command form is:

```bash
python tools/shift_resource_pipeline.py all \
  Vehicles.zip Silverstone_Era3_.zip RENDER.bff \
  -o out/offline-pipeline \
  --track Silverstone_Era3_GrandPrix \
  --vehicle BMW_M3_E36 \
  --scene-set out/native-scene-vulkan \
  --participant-runtime-evidence out/native_physics_participant_runtime_evidence.json \
  --require-native-resource-handoff \
  --require-participant-runtime-identity
```

Outputs include:

- `vehicle_physics_resource_manifest.json` — neutral exact BFF/physics manifest;
- `native_physics_manifest.json` — current BMW native-runtime compatibility
  manifest, only when the exact BMW gate is satisfied;
- `scene_catalog_join.json` — runtime-proven scene IMB ↔ offline catalog join;
- optional `native_physics_participant_runtime_evidence.json` — exact bytes of an
  already-ready participant runtime-evidence input;
- `native_resource_handoff.json` — combined resource-input admission plus the
  separate participant-runtime-identity transport state.

If `--scene-set` is omitted, the handoff remains blocked with
`scene-set:runtime-proven-input-required`. This is intentional: the offline
resource pipeline cannot substitute static evidence for the existing runtime
scene provenance chain.

## Vertical-slice profile integration

A ready Process D output can replace the duplicated scene and physics paths in
`SHIFT.NativeVerticalSliceProfile/1`. When the native handoff also contains a
ready transported participant artifact, the profile may omit
`participant_boundary` as well:

```json
{
  "format": "SHIFT.NativeVerticalSliceProfile/1",
  "version": 1,
  "workspace_root": ".",
  "track": "Silverstone_Era3_GrandPrix",
  "vehicle": "BMW_M3_E36",
  "retail_archive_identity_admission": "out/retail_archive_identity_admission.json",
  "resource_pipeline": "out/offline-pipeline",
  "camera_state": "out/native-camera-state.json",
  "solver_frame": "out/native-solver-frame/solver_frame.sbfr",
  "generated_body_constraint_frame": "out/native-generated/generated_body_constraints.gbcf",
  "constraint_sample_relation_frame": "out/native-generated/constraint_sample_relations.csrf",
  "constraint_relation_reset_frame": "out/native-generated/constraint_relation_reset.crrf",
  "post_solve_projection": "out/native-generated/post_solve_projection.sbps",
  "persist_post_solve_body_state": true,
  "frames": 120
}
```

When `resource_pipeline` is present, explicit `scene_set` and `physics_manifest`
must be omitted. The runner requires:

- `pipeline_run.json` to be `SHIFT.OfflineResourcePipelineRun/1` with
  `native_resource_handoff_ready=true`;
- `native-handoff/native_resource_handoff.json` to be a ready
  `SHIFT.OfflineNativeResourceHandoff/1` with `resource_inputs_ready=true`;
- the recorded runtime-proven scene-set path to remain inside `workspace_root`;
- the generated native physics manifest path and SHA-256 to match the handoff
  artifact record;
- the scene set itself to contain the canonical `bundle_set_manifest.json` plus
  a ready `bundle_set_prepare.json`.

When a participant artifact is present, the runner additionally requires:

- pipeline and handoff participant readiness to agree;
- the artifact to use the canonical native-handoff path;
- the recorded artifact SHA-256 to match the actual bytes;
- the artifact to remain a ready
  `SHIFT.NativePhysicsParticipantRuntimeEvidence/1` with the registry/selector
  identity join and participant instance still ready.

A pipeline-supplied participant artifact cannot be combined with an explicit
profile `participant_boundary`; the ambiguity is rejected. If the resource
pipeline has no participant artifact, the legacy explicit `participant_boundary`
remains mandatory.

Camera state and all BODY-feedback packets remain mandatory profile inputs and
keep their existing validation gates. Resource-pipeline mode does not synthesize
or replace them.

### Target identity binding

For target-labelled profiles, the runner also binds the resource pipeline back to
the requested target instead of accepting any independently ready handoff:

- `scene_catalog_join.track` must equal the profile `track`;
- `vehicle_physics_manifest.vehicle` must equal the profile `vehicle`.

When the profile carries the Phase 711
`SHIFT.RetailArchiveIdentityAdmission/1`, those labels are the same labels that
were already revalidated against that admission immediately before pipeline
resolution. The launcher does not recompute retail archive hashes or duplicate
the Process 3 archive-occurrence algorithm.

Legacy/manual profiles without target labels remain compatible and do not gain a
new retail-identity requirement merely by using resource-pipeline mode.

The vertical-slice runner still supports the legacy explicit `scene_set`,
`physics_manifest`, and participant evidence paths when `resource_pipeline` is
absent.

## Non-claims

`SHIFT.OfflineNativeResourceHandoff/1` means only that the native render/physics
**resource inputs** have been joined to exact original-resource identities. If a
participant artifact is transported, it additionally means those already-proven
participant evidence bytes were preserved and admitted under their existing
runtime-evidence contract. It does not claim:

- camera-state readiness;
- creation of participant runtime identity from static resources;
- BODY feedback packet readiness;
- provider-present scheduling;
- full native runtime execution readiness;
- retail game-loop equivalence.

Those remain separate existing gates.