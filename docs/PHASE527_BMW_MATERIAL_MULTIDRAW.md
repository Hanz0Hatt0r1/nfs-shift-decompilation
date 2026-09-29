# Phase 527 — BMW material-slice multi-draw adaptation

Phase 527 connects the existing evidence-backed BMW material/DDS adapter to the
Phase 524–526 multi-draw Vulkan path.

## Pipeline

```text
SHIFT.BMWRealMaterialSlice/1
  -> RenderCommand submesh N
  -> existing BMW material adapter
  -> exact child DDS/resource bridge and provenance
  -> draws/submesh_NNN/SHIFT.BMWVulkanBundle/1
  -> index finalized child manifests
  -> SHIFT.BMWVulkanBundleSet/1
  -> Phase 525 prepare gate
  -> Phase 526 native multi-draw runtime
```

## Finalized-child indexing

`index_bmw_vulkan_bundle_set()` is separate from child construction. It reads
the already-written `bundle_manifest.json` for every canonical child and
computes the top-level draw manifest/hash from those final bytes.

That separation prevents a top-level set builder from recreating a child after
the material adapter has attached DDS packets, cube resources or provenance.

Missing, malformed, wrong-format or blocked child manifests remain explicit
`bundle-set:submesh-N:...` blockers.

## Material adapter set contract

`build_bmw_vulkan_set_from_material_slice()` emits
`SHIFT.BMWMaterialSliceVulkanSet/1` and:

- defaults to all RenderCommand submeshes;
- accepts an explicit ordered unique submesh list;
- materializes the source-BFF iterable once;
- runs the existing single-submesh adapter independently for every draw;
- preserves child-local DDS bridge reports and source records;
- writes `material_slice_set_source.json`;
- indexes the finalized child bundles without rebuilding them;
- keeps ready siblings visible when another draw blocks;
- marks the complete set blocked until all selected children are ready.

The single-submesh API remains unchanged. The CLI adds `--all-submeshes`.

## CI boundary

The Linux Vulkan smoke now creates its two-draw test through the material-slice
set adapter rather than directly through the generic bundle-set builder. The
result still passes Phase 525 real GLSL/SPIR-V/interface preparation and Phase
526 Xvfb/lavapipe execution.
