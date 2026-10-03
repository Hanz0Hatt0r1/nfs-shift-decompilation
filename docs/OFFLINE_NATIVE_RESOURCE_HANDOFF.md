# Offline native resource handoff

Process D now has a fail-closed bridge from the offline BFF catalog/bootstrap to
the native runtime's existing render and physics resource inputs.

Implemented in:

- `src/resources/offline_native_resource_handoff.py`;
- `tools/shift_resource_pipeline.py native-handoff`.

The bridge does **not** create runtime evidence and does not replace any renderer
provenance gate.

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

## Command

After `tools/shift_resource_pipeline.py all` has produced the resource outputs:

```bash
python tools/shift_resource_pipeline.py native-handoff \
  out/offline-pipeline/resource_catalog.json \
  out/offline-pipeline/scene_vehicle_bootstrap.json \
  out/offline-pipeline/vehicle_physics_bundle_report.json \
  --scene-set out/native-scene-vulkan \
  -o out/offline-pipeline/native-handoff
```

Outputs:

- `vehicle_physics_resource_manifest.json` — neutral exact BFF/physics manifest;
- `native_physics_manifest.json` — current BMW native-runtime compatibility
  manifest, only when the exact BMW gate is satisfied;
- `scene_catalog_join.json` — runtime-proven scene IMB ↔ offline catalog join;
- `native_resource_handoff.json` — combined resource-input admission state.

If `--scene-set` is omitted, the command remains blocked with
`scene-set:runtime-proven-input-required`. This is intentional: the offline
resource pipeline cannot substitute static evidence for the existing runtime
scene provenance chain.

## Non-claims

`SHIFT.OfflineNativeResourceHandoff/1` means only that the native render/physics
**resource inputs** have been joined to exact original-resource identities. It
does not claim:

- camera-state readiness;
- participant runtime identity;
- BODY feedback packet readiness;
- provider-present scheduling;
- full native runtime execution readiness;
- retail game-loop equivalence.

Those remain separate existing gates.
