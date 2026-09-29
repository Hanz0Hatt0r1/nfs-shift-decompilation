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

The runtime accepts either a single MGEO mesh or a prepared `SHIFT.BMWVulkanBundle/1`. Bundle mode validates the native-submission, SPIR-V and Vulkan-interface gates, preserves the packet vertex layout, loads the bundle vertex/pixel SPIR-V, uploads the `SVCP` constant buffers plus `SVTP` 2D textures and optional cube, creates descriptor sets 0/1, and submits the prepared shader/material path directly. The frame loop also exposes a fixed 60 Hz simulation boundary through `SHIFT.NativeRuntimeState/1`, with evidence-shaped camera double-buffer state, vehicle control intent and a physics participant/tick boundary. The state layer deliberately does not synthesize unknown retail force/integration semantics. `Esc` or `Q` exits the harness.

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
  --physics-manifest evidence/bmw_m3_vehicle_physics_manifest.json \
  --frames 120
```

On CI or a headless workstation, run it through Xvfb.

## Design boundary

This target is deliberately small. Scene streaming and full multi-submesh RenderCommand scheduling are still separate gates. The current native state boundary already accepts the real BMW physics manifest and sizes the proven SDF workspace; numerical force/integration semantics remain a separate evidence-backed backend task.


## Phase 530 per-draw cull state

Prepared BMW bundles can contain `pipeline_state.json` with
`SHIFT.MaterialCullState/1`. The native runtime validates that sidecar and
selects `VK_CULL_MODE_NONE`, `VK_CULL_MODE_BACK_BIT` or
`VK_CULL_MODE_FRONT_BIT` independently for each material draw. The mapping is
source-backed by the retail BMT enum/string table and the retail D3D9 cull
lookup. Missing sidecars retain the legacy no-cull material path for old
fixtures; malformed or blocked sidecars fail closed.
