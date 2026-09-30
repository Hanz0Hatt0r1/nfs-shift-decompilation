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

The runtime accepts a single MGEO mesh, a prepared `SHIFT.BMWVulkanBundle/1`, the historical BMW bundle set, or a Phase 586 prepared `SHIFT.NativeSceneVulkanSet/1` via `--scene-set`. Bundle mode validates the native-submission, SPIR-V and Vulkan-interface gates, preserves the packet vertex layout, loads semantic-aware SVGP v3 geometry (while retaining v1/v2 compatibility), loads the bundle vertex/pixel SPIR-V, uploads the `SVCP` constant buffers plus `SVTP` 2D textures and optional cube, creates descriptor sets 0/1, and submits the prepared shader/material path directly. The frame loop also exposes a fixed 60 Hz simulation boundary through `SHIFT.NativeRuntimeState/1`, with evidence-shaped camera double-buffer state, vehicle control intent and a physics participant/tick boundary. The state layer deliberately does not synthesize unknown retail force/integration semantics. `Esc` or `Q` exits the harness.

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

This target is deliberately small. Prepared neutral scene scheduling is available through `--scene-set`; retail streaming/LOD, authentic runtime-proven Silverstone inputs and unresolved renderer-owned resources remain separate gates. The current native state boundary already accepts the real BMW physics manifest and sizes the proven SDF workspace; numerical force/integration semantics remain a separate evidence-backed backend task.


## Phase 530 per-draw cull state

Prepared BMW bundles can contain `pipeline_state.json` with
`SHIFT.MaterialCullState/1`. The native runtime validates that sidecar and
selects `VK_CULL_MODE_NONE`, `VK_CULL_MODE_BACK_BIT` or
`VK_CULL_MODE_FRONT_BIT` independently for each material draw. The mapping is
source-backed by the retail BMT enum/string table and the retail D3D9 cull
lookup. Missing sidecars retain the legacy no-cull material path for old
fixtures; malformed or blocked sidecars fail closed.


## Phase 532 depth/blend state

`SHIFT.MaterialPipelineState/1` extends the per-bundle sidecar with proven
retail depth-test/write/compare and ordinary alpha-blend factors/operations.
The native runtime consumes these values independently for every prepared draw.
Enabled alpha-test and unmapped/bias state are rejected by bundle preparation
rather than approximated.


## Vulkan validation on Linux

Install `vulkan-validationlayers` (Ubuntu/Debian), then add `--validation` to
`shift_runtime`. The runtime requires `VK_LAYER_KHRONOS_validation` and
`VK_EXT_debug_utils` when requested; missing support fails startup. Validation
errors, including resource destruction errors, produce a nonzero exit status.
The final frame-loop report includes `validation_enabled` and
`validation_errors`; warnings are written to stderr without failing the run.

A software Vulkan smoke run, from the repository root:

```bash
python3 tools/run_linux_vulkan_smoke.py out/vulkan/bundle --validation
xvfb-run -a native_runtime/build/shift_runtime \
  --bundle-set out/vulkan/bundle/bundle_set \
  --shader-dir native_runtime/build/shaders \
  --physics-manifest evidence/bmw_m3_vehicle_physics_manifest.json \
  --frames 120 --validation
```

Build `native_vulkan` first for bundle preparation. Select Mesa lavapipe using
`VK_ICD_FILENAMES` if the machine has multiple Vulkan drivers; the ICD JSON path
varies by distribution. An existing X11 display can be used without `xvfb-run`.
The generated fixture exercises indexed draws, constants, a 2D texture and a
cubemap; it is synthetic test geometry, not a playable game scene.

Command buffers and acquire semaphores follow the frame fence. Presentation
semaphores follow the acquired swapchain image so they are not reused while
presentation still owns them, as described in the
[Khronos Vulkan guide](https://docs.vulkan.org/guide/latest/swapchain_semaphore_reuse.html).
Linux CI validates both single-draw and multi-draw runs across 12 frames.


## Phase 586 neutral scene-set mode

Prepare the Phase 585 set first:

```bash
python shift_importer.py native-scene-vulkan-prepare \
  out/native-scene-vulkan \
  --validator glslangValidator
```

Then run:

```bash
native_runtime/build/shift_runtime \
  --scene-set out/native-scene-vulkan \
  --shader-dir native_runtime/build/shaders \
  --frames 120 --validation
```

This mode requires neutral child prepare/interface gates and applies each
`world_transform.svwt` before GPU upload with the Phase 584 semantic affine
rules. The BMW `--bundle-set` ABI remains supported independently.
