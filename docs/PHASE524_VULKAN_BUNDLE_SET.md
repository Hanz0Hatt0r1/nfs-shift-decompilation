# Phase 524 — ordered Vulkan bundle set

Phase 524 introduces `SHIFT.BMWVulkanBundleSet/1` as the fail-closed
multi-submesh preparation boundary.

## Contract

The existing `SHIFT.BMWVulkanBundle/1` remains the atomic native ABI.  A
bundle set stores one independently validated atomic bundle per selected
RenderCommand submesh under:

```text
draws/submesh_NNN/
```

and records deterministic draw order in `bundle_set_manifest.json`.

Each draw retains:

- the original RenderCommand submesh index;
- source `first_index` and `index_count`;
- the child bundle-manifest path and SHA-256;
- the shader permutation identity when present;
- the child readiness state and exact blocking reasons.

## Evidence boundary

The bundle-set layer does not merge constants, descriptor layouts, samplers or
shader permutations.  It deliberately preserves each submesh as its own
already-gated bundle so the native multi-draw executor can create the correct
per-draw pipeline and descriptor resources without inventing shared material
semantics.

A single blocked child makes the set blocked.

## Next

Consume the ordered draw set in `native_runtime/` and submit all ready draws
inside one swapchain render pass with per-draw pipelines/descriptors.
