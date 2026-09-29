# Phase 525 — Vulkan bundle-set preparation gate

Phase 525 composes the existing per-bundle Vulkan gates across every ordered
draw from `SHIFT.BMWVulkanBundleSet/1`.

For each child bundle it runs the existing preparation path:

```text
BMWVulkanBundle/1
  -> GLSL -> SPIR-V
  -> SPIR-V reflection
  -> descriptor/resource interface gate
  -> native-submission provenance gate
```

The result is `SHIFT.BMWVulkanBundleSetPrepare/1` in
`bundle_set_prepare.json`.

## Fail-closed rules

Preparation is blocked when:

- the set manifest or draw-order sidecar is missing;
- the set itself is not ready;
- draw count/order differs between JSON and `bundle_set.paths`;
- a child path is absolute or traverses through `..`;
- any child compile/reflection/interface/provenance gate blocks;
- a supposedly ready child does not emit both `spirv_report.json` and
  `vulkan_interface.json`.

No shader, sampler or descriptor compatibility is inferred between draws.
Every draw keeps its own validated child state.

## Next

The native runtime can now consume only sets with a ready Phase 525 report and
instantiate one pipeline/descriptor/resource block per ordered draw.
