# Phase 577 — runtime-proven Silverstone native bundle

Phase 576 closes the exact runtime shader-admission → scene primitive →
RenderCommand join. Phase 577 freezes those proven draws into the ordered
atomic-bundle ABI already consumed by `native_runtime`.

## Existing native ABI

The Linux runtime already consumes:

- atomic `SHIFT.BMWVulkanBundle/1`;
- ordered `SHIFT.BMWVulkanBundleSet/1`;
- `SHIFT.BMWVulkanBundleSetPrepare/1`.

Those names are legacy BMW names, but the binary packets underneath
(`SVGP`, `SVCP`, `SVTP`, SPIR-V/interface gates) are renderer-neutral.

Phase 577 deliberately reuses that ABI instead of adding a second native
executor.

## Exact neutral-resource extension

`build_bmw_vulkan_bundle()` keeps its legacy BMW behavior by default.

A new explicit `expected_mesh_ref` argument permits another resource only
when the RenderCommand mesh reference equals that exact value. The mesh payload
may be:

- `SHIFT.MEB`;
- `SHIFT.NeutralMesh/1`.

This is not an "accept anything" mode. The scene adapter passes the exact IMB
resource reference already proven by the SGB/Phase 576 path.

## Vulkan shader provenance

`translate_pair_blob()` already emitted Vulkan-target GLSL, but
`SHIFT.RenderCommand/1` previously retained only the GLES/debug shader
sources.

Phase 577 now preserves:

- `vulkan_vertex_glsl`;
- `vulkan_pixel_glsl`.

The atomic bundle writer prefers these Vulkan sources and only uses the legacy
fallback for older contracts.

## Silverstone adapter

The new contract is:

`SHIFT.SilverstoneNativeSceneBundle/1`

implemented by:

`src/scene/silverstone_native_scene_bundle.py`.

Input:

- Phase 576 `SHIFT.SGBRenderBindingBridge/1`;
- the extracted/analyzed IR root.

For each exact runtime-proven IMB draw it:

1. verifies the Phase 576 runtime shader join is ready;
2. resolves the exact IMB manifest row;
3. reads the raw decoded IMB payload and rechecks SHA-256;
4. rebuilds source-backed `SHIFT.IMBNeutralGeometry/1`;
5. resolves material texture IDs back to exact DDS resources in the IR;
6. decodes supported DDS base-level payloads;
7. builds one existing atomic native bundle for the exact scene resource;
8. indexes ready children into the existing ordered bundle-set ABI.

## Proven-subset policy

A full Silverstone frame does not need to be captured before the pipeline can
make useful native progress.

Only submeshes carrying the Phase 576 marker:

`runtime_shader_admission.selection_source = "runtime-admission"`

are eligible.

Unproven submeshes are excluded and reported. They are never inserted using
static shader ranking.

A blocked proven child (for example missing DDS support or renderer-global cube
state) is also excluded from the executable set and retains explicit blockers.

The wrapper therefore distinguishes:

- `ready`: the adapter safely produced at least one proven child with no
  adapter-level blocker;
- `bundle_set_ready`: the legacy ordered set can be consumed by preparation;
- `coverage_complete`: every IMB submesh represented by the bridge was
  included;
- `native_execution_ready`: the optional Phase 525 compile/interface prepare
  gate also passed.

## Scene transforms

Every included draw preserves its source-backed world matrix in the Phase 577
wrapper.

The current native bundle executor does **not** apply per-draw SGB world
matrices. The geometry packet also retains its existing geometry-checkpoint
normalization.

Therefore Phase 577 explicitly records:

- `world_matrix_provenance_preserved = true`;
- `world_matrix_applied_by_native_runtime = false`;
- `scene_transform_parity = false`.

A successful Phase 577 bundle is a material/geometry execution checkpoint, not
a claim that Silverstone is already rendered in correct world space.

## Texture boundary

Material 2D texture bindings are resolved through the existing
`RenderResources/1` texture IDs back to exact IR manifest rows and decoded
through the existing DDS reference decoder.

External renderer-global resources remain explicit. In particular, a required
cube sampler still blocks an atomic child unless an explicit
`SHIFT.ReferenceCubeTexture/1` is supplied.

## CLI

```bash
python shift_importer.py silverstone-native-scene-bundle \
  out/scene-render-binding.json \
  out/ir \
  out/silverstone-native \
  --prepare \
  --validator glslangValidator
```

When `--prepare` is used, the adapter also executes the existing
`SHIFT.BMWVulkanBundleSetPrepare/1` compile/reflection/interface gate.

The resulting directory can be supplied to the existing runtime with
`--bundle-set` once `native_execution_ready=true`.

## Next

The next native scene step is to transport the preserved per-draw world matrix
through the bundle ABI and apply it in `native_runtime` before indexed
submission.

That phase must remove geometry-checkpoint normalization from the scene path or
make its interaction with world transforms explicit before any world-space
Silverstone rendering claim is made.
