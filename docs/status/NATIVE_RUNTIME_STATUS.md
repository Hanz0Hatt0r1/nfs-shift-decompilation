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

The executable emits `SHIFT.NativeRuntimeBootstrap/1` and `SHIFT.NativeRuntimeFrameLoop/1` records. Bundle mode now consumes the prepared `SHIFT.BMWVulkanBundle/1` end-to-end for the supported interface slice: native-submission/SPIR-V/interface gates, full vertex packet layout, bundle SPIR-V modules, `SVCP` constants, `SVTP` 2D textures, optional cube, descriptor sets and indexed submission. The frame loop has a fixed 60 Hz simulation boundary and neutral `SHIFT.NativeRuntimeInput/1` keyboard state. The new `SHIFT.NativeRuntimeState/1` layer carries evidence-shaped camera double-buffer state, vehicle control intent, and a physics participant/tick boundary. Native runtime can also consume the repository's real `SHIFT.BMWM3VehiclePhysicsResourceManifest/1` and prepare the proven 40-scalar SDF workspace (matrix-pool and row-pointer sizing), while intentionally stopping before inventing unresolved retail force integration/provider semantics.

## Deliberate exclusions

The Linux target does not require EA services, online functionality, DRM, login/profile/cloud services, matchmaking or Bink/video playback for the test build.

## Next integration gates

1. Generalize the native material executor from the current validated bundle interface to multiple RenderCommand submeshes and shader permutations without introducing BFF parsing into the runtime.
2. Connect the existing evidence-backed camera update/snapshot contracts to the native state double buffer.
3. Connect the vehicle physics participant registry/selector boundary to the native state without synthesizing unresolved provider semantics.
4. Connect the real BMW SDF solver domain/workspace contract to the fixed tick once a native numerical backend is available.
5. Connect scene/track resource loading.
6. Add keyboard/gamepad vehicle controls beyond the neutral intent layer.
7. Expand native depth, blend, sampler-state and shader-resource execution, then replace the bounded frame loop with the native game loop/state machine.

The renderer remains downstream of normalized IR; original BFF parsing stays outside the native executable.
