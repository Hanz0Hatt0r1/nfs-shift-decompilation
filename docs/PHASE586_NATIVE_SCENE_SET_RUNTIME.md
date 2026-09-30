# Phase 586 — native_runtime neutral scene-set execution

Phase 585 closes preparation of `SHIFT.NativeSceneVulkanSet/1` without
relabeling its neutral `SHIFT.VulkanDrawBundle/1` children as BMW bundles.

Phase 586 consumes that prepared contract directly in the offline Linux runtime.

## Runtime admission

`native_runtime/shift_runtime` adds a fourth mutually-exclusive input mode:

```text
--scene-set DIR
```

The existing modes remain:

- `--mesh`;
- `--bundle`;
- `--bundle-set` for the historical BMW multi-draw contract.

Scene-set mode requires:

- `SHIFT.NativeSceneVulkanSet/1` ready;
- `SHIFT.NativeSceneVulkanSetPrepare/1` ready in
  `bundle_set_prepare.json`;
- matching non-empty draw counts;
- safe ordered paths from `bundle_set.paths`;
- one neutral `SHIFT.VulkanDrawBundle/1` per path;
- one ready `SHIFT.VulkanDrawBundlePrepare/1` per neutral child;
- ready native-submission, SPIR-V and neutral interface gates.

The bootstrap record reports:

`geometry_source = "SHIFT.NativeSceneVulkanSet/1"`

and exposes `scene_set_mode=true` independently of BMW
`bundle_set_mode`.

## Neutral interface gate

The native material loader now accepts either:

- `SHIFT.BMWVulkanInterfaceGate/1`;
- `SHIFT.VulkanInterfaceGate/1`.

This is selected by prepared child artifacts rather than by pretending the
neutral scene bundle is BMW-specific.

## SVWT execution inside native_runtime

Phase 584 proved semantic-aware affine execution in the standalone Vulkan
material executor. Phase 586 ports that exact execution contract into the
runtime geometry-load path before vertex-buffer upload.

The same fail-closed rules apply:

- finite D3D row-vector affine matrices only;
- singular linear transforms rejected;
- POSITION 200 uses affine point math;
- NORMAL 220 uses inverse-transpose and normalization;
- TANGENT 240 / TANGENT2 250 use the linear part and normalization;
- semantic-unknown legacy multi-attribute affine geometry remains blocked.

The source `world_transform.svwt` is not mapped to an invented retail
constant register. It is consumed as the already-proven native scene transform
sidecar.

## Ordering

The runtime preserves the Phase 580/585 `bundle_set.paths` order and creates
one independent material draw per child. Children retain independent:

- geometry/index buffers and draw ranges;
- SPIR-V modules;
- constant buffers;
- texture/cube resources;
- pipeline state;
- descriptor sets.

They share the existing swapchain/render-pass/frame synchronization path.

## Phase 585 handoff update

`SHIFT.NativeSceneVulkanSetPrepare/1` now reports:

`native_runtime_scene_set_loader_available = true`.

Preparation still does not execute a scene; the flag only states that its exact
output format now has a native consumer.

## Linux CI

The Linux Vulkan workflow now creates a neutral prepared one-child scene set,
including:

- exact child manifest SHA;
- `SHIFT.VulkanDrawRuntimeProvenanceGate/1`;
- exact SVWT packet identity;
- neutral child prepare;
- neutral scene-set prepare.

It then executes three validated frames through:

```bash
shift_runtime --scene-set ...
```

The existing BMW single-draw and BMW bundle-set smoke paths remain intact.

## Boundary

Phase 586 closes native scheduling/execution for already-proven neutral scene
draws. It does not create runtime-proven Silverstone draws by itself.

The immediate external scene gate remains an authentic Silverstone D3D9
capture. Renderer-owned external resources, unresolved per-instance
MatrixNumber history, scene streaming/LOD and the IMX XML adapter remain
independent blockers.
