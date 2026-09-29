# Native Linux runtime status

## Milestone

The initial offline Linux runtime shell is now implemented as `native_runtime/`.

Current slice:

```
MGEO
  ↓
native_ir
  ↓
XCB window
  ↓
Vulkan surface / swapchain
  ↓
indexed geometry submission
  ↓
bounded frame loop
```

The executable emits `SHIFT.NativeRuntimeBootstrap/1` and `SHIFT.NativeRuntimeFrameLoop/1` records. Bundle mode now consumes the prepared `SHIFT.BMWVulkanBundle/1` end-to-end for the supported interface slice: native-submission/SPIR-V/interface gates, full vertex packet layout, bundle SPIR-V modules, `SVCP` constants, `SVTP` 2D textures, optional cube, descriptor sets and indexed submission. The frame loop has a fixed 60 Hz simulation boundary and neutral `SHIFT.NativeRuntimeInput/1` keyboard state.

## Deliberate exclusions

The Linux target does not require EA services, online functionality, DRM, login/profile/cloud services, matchmaking or Bink/video playback for the test build.

## Next integration gates

1. Generalize the native material executor from the current validated bundle interface to multiple RenderCommand submeshes and shader permutations without introducing BFF parsing into the runtime.
2. Connect scene/track resource loading.
3. Connect reconstructed camera state/update contracts.
4. Connect vehicle physics participant + solver tick to the fixed simulation boundary.
5. Add keyboard/gamepad vehicle controls.
6. Expand native depth, blend, sampler-state and shader-resource execution beyond the current bundle contract.
7. Replace the bounded test frame loop with the native game loop and state machine.

The renderer remains downstream of normalized IR; original BFF parsing stays outside the native executable.
