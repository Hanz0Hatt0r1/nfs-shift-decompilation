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

The executable emits `SHIFT.NativeRuntimeBootstrap/1` and `SHIFT.NativeRuntimeFrameLoop/1` records. Bundle mode now consumes the existing `SHIFT.BMWVulkanBundle/1` geometry packet after checking the `SHIFT.NativeSubmissionGate/1` manifest gate.

## Deliberate exclusions

The Linux target does not require EA services, online functionality, DRM, login/profile/cloud services, matchmaking or Bink/video playback for the test build.

## Next integration gates

1. Use the existing BMW `RenderCommand/1` bundle path as the native geometry source; material/shader execution is still the next gate.
2. Connect scene/track resource loading.
3. Connect reconstructed camera state/update contracts.
4. Connect vehicle physics participant + solver tick.
5. Add keyboard/gamepad vehicle controls.
6. Add depth, material, texture and shader permutation execution.
7. Replace the bounded test frame loop with the native game loop and state machine.

The renderer remains downstream of normalized IR; original BFF parsing stays outside the native executable.
