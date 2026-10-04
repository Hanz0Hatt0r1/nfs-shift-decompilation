# Phase 648 — runtime vehicle Vulkan wiring

## Playable-slice blocker reduced

Phase 646 provides the exact dynamic vehicle transform ABI and immutable-object
transform executor. Merged Process 3 Phase 647 (#1207) provides the fail-closed
live Vulkan upload primitive, but intentionally stops before the monolithic
`shift_runtime.cpp` frame loop.

Phase 648 closes that renderer-side runtime wiring gap:

```text
explicit per-step VehicleWorldMatrix
-> authoritative vehicle draw groups
-> immutable raw object-space SVGP v3 geometry
-> wait for all in-flight runtime fences
-> Phase 647 upload_live_vehicle_vertex_buffers()
-> existing shift_runtime Vulkan draw buffers
-> runtime.frame()
```

The GPU write implementation remains owned by Phase 647. Phase 648 does not add
another `vkMapMemory` implementation.

## Exact runtime attachment

`native_runtime/src/shift_runtime.cpp` currently has one executable
`native_state.fixed_step(intent)` call. A source-specific forced include attaches
`phase648_after_fixed_step(...)` immediately after that existing shell step.

The ordinary runtime remains unchanged unless
`SHIFT_NATIVE_VEHICLE_WORLD_TRANSFORM_SCRIPT` is explicitly present. This script
source is a deterministic integration regression producer, not retail gameplay
evidence and not proof of retail fixed-step/outer-update cadence.

## Immutable baseline

The normal scene loader applies startup SVWT before GPU buffer creation, so those
startup bytes cannot be reused as the dynamic baseline. Phase 648 reloads only
explicit `vehicle` draws from their raw `geometry.svpk` packets and requires
semantic SVGP v3. It verifies stride, payload size and attribute count against the
already admitted startup draw before retaining the raw bytes.

Each frame therefore delegates to Phase 647 with the same immutable object-space
bytes. Dynamic transforms do not accumulate on previously transformed vertices.

## Synchronization

The runtime uses shared host-visible/coherent vertex allocations while frames may
still be in flight. Before calling the Phase 647 uploader, Phase 648 waits for all
runtime frame fences with `vkWaitForFences(..., VK_TRUE, UINT64_MAX)`.

This scheduling responsibility belongs to the runtime wrapper; the reusable
Phase 647 upload primitive intentionally knows nothing about the runtime's frame
ownership model.

## Current retail boundary

Phase 648 does not make any blocked upstream proof positive. In particular it
does not:

- prove the retail `FUN_00765470` BODY-owner receiver identity;
- produce `SHIFT.BMWBody0BindFrameProof/1`;
- auto-commit Phase 706 from the shell `fixed_step()` path;
- prove that shell `fixed_step()` is the retail outer-update cadence;
- replace any of the nine external Phase 699/701 physics providers;
- enable camera follow.

The matrix type accepted by the runtime path is the same Phase 646
`VehicleWorldMatrix` stored by the Phase 706 persistent snapshot. Once the
upstream identity/bind/scheduling proofs become positive, the script producer can
be replaced without another renderer matrix convention or Vulkan upload path.

## Regression coverage

The Phase 648 source contract requires:

- delegation to merged `SHIFT.LiveVehicleVertexBufferUpload/1`;
- no second `vkMapMemory` implementation in the runtime adapter;
- authoritative `bundle_set.groups` and `bundle_set.paths` use;
- raw SVGP v3 object-space baseline loading;
- all-frame-fence synchronization before upload;
- exactly one current `native_state.fixed_step(intent)` attachment point;
- inert behavior without the explicit transform-script environment variable.

The dedicated native-render workflow additionally executes the real Vulkan path
under llvmpipe/Xvfb for three distinct matrices and requires three synchronized
vehicle uploads with zero validation errors.
