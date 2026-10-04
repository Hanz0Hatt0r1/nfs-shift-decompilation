# Phase 649 — freshness-gated persistent vehicle Vulkan upload

## Blocker reduced

Process 3 Phase 648 (#1209) already wires the explicit Phase 646 transform-script
producer into the real `shift_runtime` frame loop and delegates live writes to
Phase 647.

Phase 648 intentionally stops at ABI compatibility with Phase 706. Phase 649
adds the production-facing join that was still missing:

```text
PersistentBmwVehicleWorldTransformState
+ current NativeRuntimeState
        |
        v
Phase 706 read_current_bmw_vehicle_world_transform()
        |
        | stale -> reject before GPU access
        v
wait all in-flight Vulkan fences
        |
        v
Phase 647 upload_live_vehicle_vertex_buffers()
```

Contract:

```text
SHIFT.PersistentVehicleVulkanUpload/1
```

## Why this is separate from Phase 648

Phase 648 is the active renderer integration smoke and explicit script producer.
It does not consume `PersistentBmwVehicleWorldTransformState`; its telemetry only
states that the Phase 706 matrix ABI is compatible.

Phase 649 consumes the actual Phase 706 freshness contract. It does not add a
second scene loader, script hook, transform convention, or Vulkan uploader.

## Fail-closed ordering

`upload_current_bmw_vehicle_world_transform_to_vulkan(...)` first calls:

```text
read_current_bmw_vehicle_world_transform(state, runtime)
```

That existing Phase 706 gate rejects drift in:

- BODY index/cardinality;
- pose snapshot generation;
- explicit outer-update count;
- BODY0 origin;
- BODY0 basis.

Only after the read succeeds does Phase 649 wait all supplied frame fences with
`vkWaitForFences(..., VK_TRUE, UINT64_MAX)` and call the merged Phase 647 upload
primitive.

Therefore stale persistent transform state cannot map or mutate vertex memory.

## Real Vulkan regression

`persistent_vehicle_vulkan_upload_check.cpp` creates real
`HOST_VISIBLE|HOST_COHERENT` Vulkan vertex memory and two signaled frame fences.
It proves:

1. a current Phase 706 snapshot updates only the `vehicle` draw;
2. the Phase 706 commit generation survives the handoff;
3. track bytes remain unchanged;
4. stale snapshot generation is rejected with vehicle bytes unchanged;
5. changed BODY0 origin with reused generations is rejected with vehicle bytes
   unchanged;
6. missing fence synchronization is rejected with vehicle bytes unchanged.

## Current retail status

Process 1 #1208 has made retail BODY-owner identity positive through:

```text
vehicle base + 0x339c -> BODY-array owner -> BMW chassis BODY 0
```

The remaining semantic transform blocker is the independent positive
`SHIFT.BMWBody0BindFrameProof/1` plus source-backed Phase 706 commit scheduling.
When those become available, Phase 649 can consume the resulting persistent state
without another renderer integration layer.

Phase 649 does not claim the BODY0 bind matrix, bind initializer, outer-update
cadence, transform commit schedule, camera follow, or any missing physics
producer. It does not execute the original game and requires no new runtime
capture.
