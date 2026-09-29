# SHIFT native Linux runtime

This is the first integrated offline runtime shell for the Linux build target.

## Scope

The executable is intentionally offline-only. It does not provide or depend on:

- EA services;
- DRM;
- login/profile/cloud services;
- matchmaking or online networking;
- Bink/video playback.

## Current vertical slice

```
MGEO → native IR → XCB window → Vulkan swapchain → indexed draw → frame loop
```

The renderer consumes normalized native IR. Original BFF parsing remains upstream in the existing Python importer/resource pipeline.

The first slice accepts either a single MGEO mesh or a prepared `SHIFT.BMWVulkanBundle/1`. Bundle mode validates the manifest/native-submission gate and consumes `geometry.svpk`, including its `first_index` draw range. `Esc` or `Q` exits the harness.

## Build

```bash
cmake -S native_runtime -B native_runtime/build -DCMAKE_BUILD_TYPE=Release
cmake --build native_runtime/build --parallel
```

## Run

```bash
native_runtime/build/shift_runtime \
  --bundle out/example-bundle \
  --shader-dir native_runtime/build/shaders \
  --frames 120
```

On CI or a headless workstation, run it through Xvfb.

## Design boundary

This target is deliberately small. It establishes the native process/window/frame-loop boundary before scene streaming, camera state, vehicle physics and full RenderCommand submission are connected.
