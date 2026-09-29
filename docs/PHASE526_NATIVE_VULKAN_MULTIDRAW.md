# Phase 526 — native Vulkan multi-draw execution

Phase 526 consumes the Phase 524/525 ordered bundle-set contract directly in
`native_runtime/shift_runtime`.

## Admission

`--bundle-set DIR` requires all of the following:

- ready `SHIFT.BMWVulkanBundleSet/1`;
- ready `SHIFT.BMWVulkanBundleSetPrepare/1`;
- matching non-zero top-level draw counts;
- a `bundle_set.paths` entry for every draw;
- relative child paths with no parent traversal;
- the existing ready child bundle, SPIR-V and interface gates.

No original BFF/MEB/BMT/FXO parsing is added to the native runtime.

## GPU ownership

Every draw owns its own:

- geometry buffers and indexed draw range;
- vertex/pixel constant buffers;
- texture/cube images and samplers;
- descriptor layouts, pool and descriptor sets;
- vertex/pixel shader modules;
- pipeline layout and graphics pipeline.

The swapchain, render pass, depth buffers, command buffers and synchronization
remain frame-global.

## Submission

One command buffer begins one depth-tested render pass and iterates the
prepared draws in `bundle_set.paths` order. For every draw the runtime binds
that draw's pipeline, geometry and descriptor sets before
`vkCmdDrawIndexed`.

The legacy `--bundle` mode now follows the same code path with a single
material draw, keeping the atomic bundle ABI backward compatible.

## CI

The Linux Vulkan workflow builds a synthetic two-submesh bundle set, performs
the real Phase 525 glslang/reflection/interface preparation, then launches the
XCB/Vulkan runtime under Xvfb and requires three frames with
`material_draws = 2`.
