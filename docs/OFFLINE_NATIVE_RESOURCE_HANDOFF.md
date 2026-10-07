# Offline native resource handoff

Process D now has a fail-closed bridge from the offline BFF catalog/bootstrap to
the native runtime's existing render and physics resource inputs.

Implemented in:

- `src/resources/offline_native_resource_handoff.py`;
- `src/resources/offline_native_participant_handoff.py`;
- `tools/shift_resource_pipeline.py native-handoff`;
- `tools/run_native_vertical_slice.py` resource-pipeline profile mode.

The bridge does **not** create runtime evidence and does not replace any renderer
provenance gate. Existing participant runtime evidence may be transported through
the handoff as a separate readiness axis, but it is never inferred from static
resources.

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

## Participant runtime evidence transport

A ready existing `SHIFT.NativePhysicsParticipantRuntimeEvidence/1` can be supplied
with `--participant-runtime-evidence`. The pipeline copies the exact bytes into
the native handoff, records source/copy SHA-256, and requires:

- `ready=true`;
- `registry_selector_identity_join_proven=true`;
- `participant_instance_ready=true`.

This is transport only. Invalid or missing participant evidence does not change
`resource_inputs_ready`; `participant_runtime_identity_ready` remains a separate
runtime-evidence axis. `--require-participant-runtime-identity` can make the CLI
return non-zero unless that transported axis is ready.

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
- `native_resource_handoff.json` — combined resource-input admission state;
- `native_physics_participant_runtime_evidence.json` — byte-exact transported
  participant evidence when a ready source is supplied.

If `--scene-set` is omitted, the handoff remains blocked with
`scene-set:runtime-proven-input-required`. This is intentional: the offline
resource pipeline cannot substitute static evidence for the existing runtime
scene provenance chain.

## Vertical-slice profile integration

A ready resource-pipeline output can now replace the three duplicated
resource-bound paths in a prepared `SHIFT.NativeVerticalSliceProfile/1`:

```json
{
  "format": "SHIFT.NativeVerticalSliceProfile/1",
  "version": 1,
  "workspace_root": ".",
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

When profile preparation uses `resource_pipeline`, `scene_set`,
`physics_manifest`, and `participant_boundary` are omitted so the pipeline has a
single authority for those resource-bound inputs. The profile builder validates
only that the pipeline directory is workspace-local and exists; full handoff
validation remains deferred to `tools/run_native_vertical_slice.py`.

The runner requires:

- `pipeline_run.json` to be `SHIFT.OfflineResourcePipelineRun/1` with
  `native_resource_handoff_ready=true`;
- `native-handoff/native_resource_handoff.json` to be a ready
  `SHIFT.OfflineNativeResourceHandoff/1` with `resource_inputs_ready=true`;
- the recorded runtime-proven scene-set path to remain inside `workspace_root`;
- the generated native physics manifest path and SHA-256 to match the handoff
  artifact record;
- the scene set itself to contain the canonical `bundle_set_manifest.json` plus
  a ready `bundle_set_prepare.json`;
- when participant evidence is transported, its canonical handoff path and
  SHA-256 to match, its format to be
  `SHIFT.NativePhysicsParticipantRuntimeEvidence/1`, and its identity/instance
  readiness gates to remain positive;
- for targeted profiles, the handoff scene/vehicle target labels to match the
  profile `track`/`vehicle` identity.

Camera state and all BODY feedback packets remain mandatory profile inputs and
keep their existing validation gates. Resource-pipeline mode does not create or
replace them.

For compatibility, a manually authored resource-pipeline profile may still use
an explicit `participant_boundary` only when the selected handoff does not carry
a participant runtime-evidence artifact. If the pipeline already supplies that
artifact, an explicit participant path is rejected as ambiguous. The profile
preparation path intentionally uses the stricter single-authority form shown
above.

The vertical-slice runner still supports the legacy explicit `scene_set`,
`physics_manifest`, and `participant_boundary` profile fields when
`resource_pipeline` is absent.

## Non-claims

`SHIFT.OfflineNativeResourceHandoff/1` means only that the native render/physics
**resource inputs** have been joined to exact original-resource identities. Its
base `ready` / `resource_inputs_ready` state does not itself claim:

- camera-state readiness;
- participant runtime identity readiness (even when that evidence is transported
  as a separate ready axis);
- BODY feedback packet readiness;
- provider-present scheduling;
- full native runtime execution readiness;
- retail game-loop equivalence.

Those remain separate existing gates.
