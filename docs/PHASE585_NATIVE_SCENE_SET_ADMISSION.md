# Phase 585 — neutral scene-set admission into native_runtime

Phase 584 closes the affine world-transform math in the standalone native
material executor. The remaining integration gap was scheduling: the offline
runtime still admitted only the historical BMW atomic/set formats even though
Phase 579–580 already produced neutral scene children.

Phase 585 closes that gap without relabeling Silverstone/IMB data as BMW/MEB.

## Contract

The scene path is now:

```text
SHIFT.NativeSceneVulkanSet/1
  → SHIFT.NativeSceneVulkanSetPrepare/1
  → ordered SHIFT.VulkanDrawBundle/1 children
  → native_runtime --scene-set
```

`SHIFT.NativeSceneVulkanSetPrepare/1` is implemented by
`src/scene/native_scene_vulkan_prepare.py`.

It validates:

- the neutral scene-set format/readiness;
- deterministic draw count and `bundle_set.paths` order;
- relative/non-escaping child paths;
- neutral `SHIFT.VulkanDrawBundle/1` child identity;
- child SPIR-V compilation/reflection;
- descriptor/resource interface readiness;
- required SVWT sidecars;
- unresolved renderer-owned external-resource blockers.

The existing BMW set path remains separate and unchanged.

## Generic child gates

The historical helper names
`compile_bmw_vulkan_bundle`,
`validate_bmw_vulkan_interface` and
`run_bmw_vulkan_bundle` remain for API compatibility.

Their format gates now admit both:

- `SHIFT.BMWVulkanBundle/1`;
- `SHIFT.VulkanDrawBundle/1`.

The emitted SPIR-V/interface contracts stay compatible with the existing native
consumer. No BMW resource identity is synthesized for neutral children.

## Native runtime

`native_runtime/shift_runtime` adds:

```text
--scene-set DIR
```

This mode is distinct from `--bundle-set`.

For a neutral scene set the runtime requires:

- `SHIFT.NativeSceneVulkanSet/1` ready;
- `SHIFT.NativeSceneVulkanSetPrepare/1` ready;
- exact ordered child paths;
- child native-submission/SPIR-V/interface gates;
- neutral `SHIFT.VulkanDrawBundle/1` child manifests.

The runtime then creates one material draw per child in the existing shared
swapchain/render-pass scheduler.

## SVWT execution

Phase 585 ports the already-proven Phase 584 affine SVWT algorithm into the
runtime geometry load path before GPU upload.

The same fail-closed rules are retained:

- D3D row-vector affine matrix only;
- non-finite/singular matrices rejected;
- POSITION property 200 → affine point transform;
- NORMAL 220 → inverse-transpose + normalize;
- TANGENT 240 / TANGENT2 250 → linear transform + normalize;
- non-position affine execution requires semantic-aware SVGP data.

This is duplicated execution of a proven contract, not a new transform
interpretation.

## Scene-set packaging correction

`SHIFT.NativeSceneVulkanSet/1` now writes child paths relative to the set root.
The old absolute/anchored representation could not pass the existing safe-path
runtime policy.

World-transform serialization is no longer itself a native-scene blocker
because this phase adds the matching runtime consumer. Unresolved external
samplers remain blockers.

## Linux CI

Linux Vulkan CI now synthesizes a neutral one-child scene set from the existing
prepared material fixture, prepares it through the neutral set gate, and runs
three validated frames with:

```text
shift_runtime --scene-set ...
```

The smoke preserves the BMW single/multi-draw regressions and adds the neutral
scene scheduling path.

## Boundary

Phase 585 proves native scheduling/admission of already runtime-proven scene
draws. It does not prove that a real Silverstone capture has supplied those
draws.

Authentic Silverstone D3D9 evidence, renderer-owned external resources,
per-instance MatrixNumber update history, streaming/LOD and the IMX XML adapter
remain independent gates.
