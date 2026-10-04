# Phase 647 — live vehicle Vulkan vertex-buffer upload

## Playable-slice blocker reduced

Phase 646 closes the renderer-side CPU transform core:

```text
one complete D3D row-vector vehicle world matrix
  -> exact source_group=vehicle draw indices
  -> immutable object-space vehicle geometry
  -> non-cumulative transformed vertex bytes
```

The native runtime already allocates draw vertex buffers from
`HOST_VISIBLE|HOST_COHERENT` Vulkan memory.  The missing renderer mechanism is
therefore not another transform convention or a staging architecture.  It is a
safe byte upload into only the authoritative vehicle draw allocations.

Phase 647 adds that reusable mechanism:

```text
SHIFT.LiveVehicleVertexBufferUpload/1
```

No original game execution and no new runtime capture are used.

## API

New files:

```text
native_runtime/include/shift_live_vehicle_vertex_buffer_upload.hpp
native_runtime/src/live_vehicle_vertex_buffer_upload.cpp
native_runtime/tests/live_vehicle_vertex_buffer_upload_check.cpp
```

The boundary consumes:

- the exact ordered draw-group rows already emitted by Phase 646;
- one immutable `VehicleObjectGeometry` baseline for every ordered draw;
- one live `VkDeviceMemory` target and exact vertex payload byte count for every
  ordered draw;
- one validated Phase 646 `VehicleWorldMatrix`.

It returns the exact vehicle draw indices and total uploaded byte count.

## Exact vehicle selection

The uploader reuses Phase 646 `vehicle_draw_indices()` and therefore does not
identify vehicle buffers from filenames, material names, draw order, MEB names,
or heuristics.

Only rows explicitly marked:

```text
vehicle
```

are mapped and written. Track allocations remain byte-identical.

Unknown group names, count drift, and scenes with no vehicle draw fail closed.

## Immutable baseline / non-cumulative update

For every vehicle draw the uploader calls the existing Phase 646
`apply_vehicle_world_transform()` on the immutable object-space
`VehicleObjectGeometry` supplied by the scene loader.

The bytes currently stored in the Vulkan vertex allocation are never used as
the source for the next transform. Therefore frame N+1 cannot accidentally
re-transform frame N bytes and accumulate translation/rotation/scale drift.

## Upload safety

Before writing live memory the implementation validates every selected draw:

- non-empty immutable vertex bytes;
- non-null Vulkan device and device-memory handles;
- exact payload-size equality between immutable geometry and live target;
- no aliasing of one `VkDeviceMemory` allocation by multiple vehicle draws;
- Phase 646 matrix and semantic-transform validity;
- transformed byte count remains exactly equal to the immutable payload size.

It then maps **all** selected vehicle allocations before copying any bytes. If a
`vkMapMemory()` call fails, previously mapped allocations are unmapped and no
vertex bytes have been copied yet.

After every map succeeds, each prepared transformed payload is copied and every
allocation is unmapped.

The caller contract requires the target memory to be the same
`HOST_VISIBLE|HOST_COHERENT` memory class already used by `shift_runtime`'s
`create_buffer()` path. No flush/invalidate step is introduced.

## Real Vulkan regression

The native regression creates a real Vulkan instance/device and real vertex
buffers backed by `HOST_VISIBLE|HOST_COHERENT` memory. On CI the ordinary Mesa
software Vulkan device is sufficient.

It proves:

- a `track, vehicle, track` draw set updates only the middle allocation;
- track allocations remain byte-identical;
- a translated vehicle position appears in mapped Vulkan memory;
- a second transform starts again from the immutable Phase 646 baseline rather
  than the previous GPU-visible bytes;
- payload-size mismatch fails before mutation;
- scenes with no vehicle identity fail closed;
- aliased vehicle memory is rejected;
- singular matrices remain rejected by the Phase 646 transform contract.

## Negative scope

Phase 647 does **not** claim or implement:

- positive retail `SHIFT.GlobalVehicleBodyOwnerIdentity/1`;
- a positive `SHIFT.BMWBody0BindFrameProof/1`;
- automatic Phase 706 transform commits from `fixed_step()`;
- BODY0 bind-frame inference;
- camera follow;
- shader constant ABI changes;
- a new vehicle-object heuristic;
- dynamic track transforms.

It also does not yet edit the monolithic `shift_runtime.cpp` frame loop. The new
primitive deliberately makes that final integration small: retain immutable
scene geometry and the Phase 646 draw-group sidecar, construct one target per
created material draw, then call this uploader with the current admitted vehicle
world matrix before command recording.

## Next renderer blocker

After this phase, the remaining Process 3 wiring is:

```text
scene_set startup
  -> retain immutable object-space geometry
  -> retain bundle_set.groups
  -> current admitted vehicle world matrix
  -> upload_live_vehicle_vertex_buffers()
  -> record/render existing material draws
```

The GPU mutation itself is no longer an unknown implementation boundary.
