# Native Linux runtime status

## Milestone

The initial offline Linux runtime shell is now implemented as `native_runtime/`.

The runtime is merged on main. Linux CI exercises the material-mode frame loop under Xvfb/lavapipe, including three rendered frames, three fixed simulation steps, one 2D bundle texture, the cube resource, and the admitted 40-scalar physics workspace. The merge also fixes two Vulkan create-info lifetime bugs that previously left queue-family and descriptor-set-layout pointers referring to expired stack arrays.

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

1. Close real BMW per-draw state differences that are not yet represented by the current Vulkan child pipeline (blend/cull/depth and remaining renderer-global resources).
2. Phase 599 connects the evidence-backed six-word CameraManager snapshot and guarded double-buffer swap to native state. Remaining camera work is retail timestamp/update scheduling, controller behavior, gameplay view selection/attachment and exact render/view constant integration.
3. Connect the vehicle physics participant registry/selector boundary to the native state without synthesizing unresolved provider semantics.
4. Connect the real BMW SDF solver domain/workspace contract to the fixed tick once a native numerical backend is available.
5. Connect scene/track resource loading. Phases 581–585 close SVWT transport, semantic-aware SVGP v3, affine execution and neutral scene-set preparation. Phase 586 adds direct `SHIFT.NativeSceneVulkanSetPrepare/1` ingestion through `native_runtime --scene-set`. Authentic runtime-proven Silverstone draws, unresolved renderer-owned scene resources, streaming/LOD and per-instance transform history remain.
6. Live keyboard vehicle controls already feed the neutral intent layer. Phase 600 adds a deterministic fixed-step input script and physics-boundary activity telemetry for CI. Gamepad/analog normalization and retail filtering remain.
7. Replace the bounded frame loop with the native game loop/state machine after render/state contracts stabilize.

The renderer remains downstream of normalized IR; original BFF parsing stays outside the native executable.


## Phase 526 multi-draw boundary

The runtime accepts `--bundle-set DIR` only when both
`SHIFT.BMWVulkanBundleSet/1` and
`SHIFT.BMWVulkanBundleSetPrepare/1` are ready. The ordered
`bundle_set.paths` sidecar is checked against both draw counts and cannot
contain absolute or parent-traversal paths.

Each prepared child owns independent Vulkan state:

- vertex/index buffers and draw range;
- VS/PS constant buffers;
- sampled 2D/cube images and samplers;
- descriptor set layouts/pool/sets;
- SPIR-V shader modules;
- pipeline layout and graphics pipeline.

All child draws share the swapchain, render pass, depth attachments and frame
synchronization and are submitted in recorded draw order inside one render
pass. The original `--bundle` mode uses the same path with one material draw.


## Phase 527 material-slice multi-draw boundary

The BMW material adapter can now emit
`SHIFT.BMWMaterialSliceVulkanSet/1`. Each selected RenderCommand submesh is
bridged independently into its canonical
`draws/submesh_NNN/SHIFT.BMWVulkanBundle/1` child before the top-level set is
indexed.

This ordering matters for real data: exact DDS extraction, SHA-256 provenance,
decoded texture packets, optional environment-cube resources, constants and
shader identity remain child-local. The set index reads the finalized child
manifests rather than rebuilding them, so per-material evidence is not lost.

A blocked submesh does not erase ready siblings, but the complete set remains
fail-closed until every selected child is ready. The existing single-submesh
adapter and CLI remain available; `--all-submeshes` selects the Phase 527
set path.


## Phase 586 neutral scene-set execution

The runtime now accepts `--scene-set DIR` only for a ready
`SHIFT.NativeSceneVulkanSet/1` with a ready
`SHIFT.NativeSceneVulkanSetPrepare/1` in `bundle_set_prepare.json`.

Neutral children must be `SHIFT.VulkanDrawBundle/1` with ready
`SHIFT.VulkanDrawBundlePrepare/1`, native-submission, SPIR-V and
`SHIFT.VulkanInterfaceGate/1` artifacts.

Before upload, `world_transform.svwt` is applied with the Phase 584 semantic
affine rules. BMW `--bundle-set` remains a separate compatible path.

Linux Vulkan CI executes a validated three-frame neutral scene-set smoke.


## Phase 587 scene transform execution telemetry

`SHIFT.NativeRuntimeBootstrap/1` now reports
`world_transform_draws` and `affine_world_transform_draws`.

The first counter increments only after a child SVWT has passed the existing
fail-closed runtime transform path and mutated the native geometry before GPU
upload. The second excludes translation-only matrices, so the Phase 586
non-singular affine smoke must prove that the semantic-aware affine branch
actually ran.

Linux Vulkan CI requires both counters to equal one for the neutral one-child
scene-set fixture.


## Phase 588 external sampler2D transport boundary

The native runtime binary ABI does not change in Phase 588. Explicit external
`sampler2D` snapshots are serialized as ordinary SVTP descriptor-set-1
records at their original D3D9 register, so the existing native texture upload
path consumes them without a special renderer-side resource class.

The upstream bundle metadata preserves whether each SVTP record came from a
material texture or an external runtime snapshot. Missing external resources
remain unresolved and are not synthesized by `native_runtime`.


## Phase 589 exact external sampler2D scene admission

Phase 589 does not change the native binary texture ABI. An exact scene-bound
external `sampler2D` snapshot is admitted upstream into the existing SVTP
descriptor-set-1 packet only after draw/resource/primitive/register/type/hash
and provenance revalidation. `native_runtime` consumes the resulting record
through its existing 2D texture upload path.

Unsupplied or mismatched external resources remain fail-closed, and other
renderer-owned resource types are not promoted by this phase.


## Phase 599 camera state boundary

`SHIFT.NativeRuntimeState/1` now executes the recovered CameraManager snapshot
and guarded two-buffer transition on the native fixed-step boundary. Each
native update records the six-word manager snapshot, copies/flips the camera
buffer, and clears the update guard before the step completes.

The frame-loop report exposes `camera_snapshot_count`,
`camera_native_updates`, final `camera_active_buffer`,
`camera_update_in_progress` and the explicit schedule label
`native-fixed-step-non-retail-timing`.

This is a native integration boundary only. It does not map the retail
`FUN_0080c920` timestamp source, 0x14 suppression window, absolute time unit,
or `FUN_0080c510` controller semantics onto the 60 Hz native clock.


## Phase 600 deterministic control-intent boundary

`native_runtime` accepts `--input-script FILE` with
`SHIFT.NativeRuntimeInputScript/1`. Each row supplies the complete
throttle/brake/left/right state for one contiguous native fixed step.

Without the option, the existing X11 keyboard mapping remains active. With it,
the script supplies vehicle intent while X11 continues to handle quit/window
events.

`PhysicsTickBoundary::tick()` counts active throttle, brake, left, right and
fully-neutral steps. The final frame-loop telemetry exposes those counters plus
the last control state and `input_source`, proving the deterministic input
crossed `SHIFT.NativeRuntimeState/1` rather than merely being parsed.

Linux Vulkan CI runs a five-step script and verifies the exact activity counts.
No retail controller dead-zone, analog curve, filtering, or vehicle-force
semantics are assigned.
