# Phase 659 — provenance-only scene samplerCube admission

## Playable-slice blocker reduced

Phase 593 introduced exact runtime-capture provenance for renderer-owned
Silverstone `samplerCube` at D3D9 register `s3`:

```text
runtime-proven scene draw
+ exact IMB identity
+ primitive index
+ samplerCube s3
+ six captured cube faces
+ capture provenance
→ SHIFT.NativeSceneExternalSamplerCubeSnapshots/1
→ environment_cube.svcp
```

`SHIFT.NativeSceneVulkanSet/1` still retained an older manual
`--environment-cube-dds` compatibility path. Before Phase 659, any decodable
cubemap supplied through that argument could become `selected_environment_cube`
when no Phase 593 snapshot existed. That made a filesystem-selected DDS capable
of satisfying a renderer-owned scene resource without proving that it was the
resource bound by the captured Silverstone draw.

Phase 659 removes that authority.

## Admission rule

For runtime-proven Silverstone scene construction, a renderer-owned
`samplerCube` is now satisfiable only through the exact scene snapshot contract:

```text
SHIFT.NativeSceneExternalSamplerCubeSnapshots/1
```

The manual scene-builder argument remains accepted by the CLI so old invocations
fail with an explicit diagnostic instead of silently changing argument shape.
When supplied without an exact cube snapshot, the builder reports:

```text
environment-cube:global-dds-not-runtime-proven-for-scene
```

When both the manual DDS and scene snapshots are supplied, the existing conflict
remains:

```text
environment-cube:global-dds-conflicts-with-scene-snapshots
```

The global DDS is no longer decoded or passed to `build_vulkan_draw_bundle()` by
`native_scene_vulkan_set.py`.

## Runtime resource boundary

`_external_sampler_blockers()` is now satisfied for `s3/samplerCube` only when
`resolve_draw_external_sampler_cube_snapshot()` returned an exact admitted cube.
A decodable DDS file cannot clear:

```text
external-sampler:runtime-resource-unresolved:s3:samplerCube
```

This keeps scene-set construction fail-closed until renderer-owned cube identity
is backed by runtime evidence.

## BMW compatibility is unchanged

The BMW playable composition path is intentionally separate. BMW material
resource construction uses `bridge_bmw_dds_resources()` through
`native_playable_scene_vulkan_set.py`; Phase 659 does not alter that API or its
material/environment DDS behavior.

Therefore this change removes only the Silverstone scene-resource authority
bypass. It does not remove general DDS cubemap decoding or BMW Vulkan resource
support.

## Regression coverage

`tests/test_phase659_native_scene_cube_provenance.py` supplies a syntactically
valid six-face DXT1 cubemap to a runtime-proven scene draw declaring external
`samplerCube s3`.

The regression proves that:

- the scene set remains blocked;
- the manual DDS is rejected because it lacks runtime scene provenance, not
  because DDS decoding failed;
- no external cube source is admitted;
- `s3/samplerCube` remains listed as an unresolved runtime resource;
- the set boundary explicitly records that global DDS is not scene runtime
  authority.

Existing Phase 593 coverage continues to prove that the exact snapshot contract
is admitted and serialized to `environment_cube.svcp`.

## Ownership boundary

Phase 659 is Process 3 scene/resource admission only. It does not change:

- shader permutation selection;
- ordinary material DDS identity or Phase 658 raw-payload verification;
- BMW material DDS extraction;
- BODY identity or physics scheduling;
- input processing;
- camera production;
- persistent `VehicleWorldMatrix` production or Vulkan transform transport.

## Result

A manually selected cubemap can no longer stand in for a renderer-owned
Silverstone scene resource. The native playable path must carry exact Phase 593
runtime provenance for external `samplerCube s3` before that resource can enter
the Vulkan child bundle.
