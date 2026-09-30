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

The runtime accepts a single MGEO mesh, a prepared `SHIFT.BMWVulkanBundle/1`, the historical BMW bundle set, or a Phase 586 prepared `SHIFT.NativeSceneVulkanSet/1` via `--scene-set`. Bundle mode validates the native-submission, SPIR-V and Vulkan-interface gates, preserves the packet vertex layout, loads semantic-aware SVGP v3 geometry (while retaining v1/v2 compatibility), loads the bundle vertex/pixel SPIR-V, uploads the `SVCP` constant buffers plus `SVTP` 2D textures and optional cube, creates descriptor sets 0/1, and submits the prepared shader/material path directly. The frame loop also exposes a fixed 60 Hz simulation boundary through `SHIFT.NativeRuntimeState/1`. Phase 599 executes the recovered CameraManager six-word snapshot plus guarded double-buffer flip/copy on that native boundary; Phase 600 can seed it from recovered camera scalar evidence. Phase 601 adds deterministic `SHIFT.NativeRuntimeInputScript/1` control snapshots that traverse the same vehicle-intent/physics-tick boundary as live keyboard input. Phase 602 additionally accepts `SHIFT.NativePhysicsParticipantBoundary/1` via `--participant-boundary`, admitting only the proven registry/selector ABI while keeping the concrete participant unresolved. Phase 603 adds the native `FUN_007b0f20` builtin sparse numerical backend as `shift_runtime_physics`; it is parity-tested separately and is not yet invoked as a complete vehicle frame. The state layer deliberately does not synthesize unknown retail force/integration semantics. `Esc` or `Q` exits the harness.

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
  --camera-state out/native-camera.json \
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


## Phase 600 camera evidence input

The live Phase 599 CameraManager snapshot/double-buffer scheduler accepts an
optional ready `SHIFT.NativeCameraStateBridge/1` through `--camera-state`.

The bridge can seed the recovered numeric mode/sub-index/camera-id/group state
before the fixed-step loop. It never transports or dereferences the opaque
retail camera/source reference; that native token remains zero.

The Phase 599 scheduler then snapshots, copies and flips the loaded state on the
existing native fixed-step boundary, retaining its explicit
`native-fixed-step-non-retail-timing` label.


## Phase 601 deterministic input scripts

Live X11 keyboard input still feeds the neutral `VehicleControlIntent`
boundary. For deterministic testing, the runtime additionally accepts:

```text
SHIFT.NativeRuntimeInputScript/1
0 1 0 0 0
1 1 0 0 1
2 0 1 1 0
3 0 0 1 1
4 0 0 0 0
```

Run it with:

```bash
xvfb-run -a native_runtime/build/shift_runtime \
  --scene-set out/native-scene-vulkan \
  --shader-dir native_runtime/build/shaders \
  --camera-state out/native-camera.json \
  --input-script out/native_input.script \
  --validation
```

If `--frames` is omitted, the script row count becomes the run length. If
`--frames N` is provided, `N` must match the row count exactly.

The script is native test/control infrastructure only. It does not claim retail
gamepad dead zones, analog response curves, filtering or vehicle-force
semantics.


## Phase 602 participant structural boundary

Generate the structural participant contract:

```bash
python3 src/physics/native_physics_participant_boundary.py \
  -o out/native_physics_participant_boundary.json
```

Then pass it to the runtime:

```bash
native_runtime/build/shift_runtime \
  --scene-set out/native-scene-vulkan \
  --shader-dir native_runtime/build/shaders \
  --physics-manifest evidence/bmw_m3_vehicle_physics_manifest.json \
  --participant-boundary out/native_physics_participant_boundary.json \
  --frames 120
```

The loader verifies the exact manager/selector separation and structural ABI.
It deliberately leaves `participant_ready=false`,
`participant_index=-1` and `participant_mode=-1`. A concrete retail
participant/provider still requires independent runtime evidence.


## Phase 603 native builtin sparse solver

The native build exposes a source-backed numerical backend for retail
`FUN_007b0f20`:

```bash
cmake -S native_runtime -B native_runtime/build -DCMAKE_BUILD_TYPE=Release
cmake --build native_runtime/build --parallel
ctest --test-dir native_runtime/build --output-on-failure \
  -R shift_runtime_builtin_sparse_solver
native_runtime/build/shift_runtime_builtin_solver_check
```

The check covers deterministic 3×3 and 4×4 systems plus fail-closed invalid
graph and zero-pivot cases.

The backend is not a replacement for the provider path and is not yet called
from the vehicle fixed-step loop. Full-frame use still requires exact
matrix/RHS/reset evidence and provider-absent dispatch proof.


## Phase 604 native builtin diagonal reset

The same `shift_runtime_physics` backend now contains
`apply_builtin_diagonal_reset()`, the exact recovered `FUN_007b2210`
matrix/RHS mutation.

The parity check now covers six cases and reports both retail source functions:

```bash
ctest --test-dir native_runtime/build --output-on-failure \
  -R shift_runtime_builtin_sparse_solver
native_runtime/build/shift_runtime_builtin_solver_check
```

The API accepts already-selected scalar nodes only. Retail reset-node selection
depends on the runtime constraint-sample low bit at `+0x70` and remains an
external evidence gate. The native fixed-step loop still does not fabricate
that selection or a complete BMW solver frame.


## Phase 605 provider-absent builtin solver frame

`execute_builtin_solver_frame()` composes the native source-backed numeric
kernels in recovered order:

```text
explicit reset nodes
  → FUN_007b2210-equivalent reset
  → FUN_007b0f20-equivalent solve
```

The native regression checks both a reset 3×3 system and a no-reset system in
addition to the Phase 603–604 cases.

This API requires the caller to supply exact matrix, RHS, sparse graph and
reset nodes. It does not infer provider-absent dispatch and is not yet invoked
from the game fixed-step loop.
