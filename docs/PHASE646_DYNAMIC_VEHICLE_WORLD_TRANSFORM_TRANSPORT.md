# Phase 646 — dynamic vehicle world-transform transport core

## Playable-slice blocker reduced

Phase 645 closes the static retail BMW object transform needed to build the
Silverstone + BMW composite scene.  The native runtime still bakes every SVWT
into CPU vertex bytes once during bundle loading, so a later persistent vehicle
pose cannot move the already-created BMW Vulkan buffers without either reloading
the scene or introducing a second transform path.

Phase 646 adds the reusable transport boundary needed before that live join:

```text
proven vehicle world matrix producer
  -> one complete D3D row-vector matrix per fixed step
  -> exact vehicle draw identities
  -> transform immutable object-space baseline
  -> upload only vehicle vertex bytes
  -> render
```

This phase implements and freezes the first four boundaries.  It deliberately
stops before mutating `shift_runtime` Vulkan buffers; that wiring is the next
small integration phase once this transport core is green.

No original game execution and no new runtime capture are used.

## Why this is necessary

Current `shift_runtime` calls `apply_bundle_world_transform()` while loading each
bundle.  That function changes the CPU `vertex_bytes` and the Vulkan buffer is
then created from those already-transformed bytes.  Per-frame rendering only
binds that buffer and issues `vkCmdDrawIndexed()`.

Therefore changing `world_transform.svwt` after startup cannot move the car.
The runtime needs a persistent object-space baseline and a per-step reapply path.

Phase 646 makes that reapply path independent of the still-unproven BODY -> MEB
bind frame.

## Transform script ABI

New text contract:

```text
SHIFT.NativeVehicleWorldTransformScript/1
<step> <m00> <m01> ... <m33>
```

Properties:

- steps are contiguous from zero;
- every row contains a complete 4x4 matrix;
- all values are finite;
- matrices use the already-established Phase 581/584 row-major D3D row-vector
  convention;
- the last column is `[0, 0, 0, 1]`;
- the upper 3x3 block must be non-singular.

The script is an explicit test/transport producer.  It does **not** claim that a
script is the final gameplay producer.  A later proven Phase 700/BODY world
matrix producer can feed the same native executor directly.

Python implementation:

```text
src/scene/native_vehicle_world_transform_script.py
```

## Exact vehicle draw identity

Phase 643 already records `source_group = track|vehicle` for every ordered draw.
Phase 646 serializes that authority into:

```text
bundle_set.groups
```

The file has exactly one `track` or `vehicle` line for every corresponding line
of `bundle_set.paths`.

The sidecar is generated from the exact same ordered `rows` collection used to
write the scene manifest and path list.  There is no filename, path-prefix,
material-name or draw-order heuristic in the native selector.

A ready composite scene must contain at least one `vehicle` draw.  Unknown group
names, count mismatch, missing vehicle rows and draw-order drift fail closed.

## Native transform core

New files:

```text
native_runtime/include/shift_vehicle_world_transform_transport.hpp
native_runtime/src/vehicle_world_transform_transport.cpp
native_runtime/tests/vehicle_world_transform_transport_check.cpp
```

The API transports:

```text
VehicleWorldMatrix
VehicleWorldTransformScript
VehicleVertexAttribute
VehicleObjectGeometry
VehicleWorldTransformResult
```

and exposes:

```text
load_vehicle_world_transform_script()
load_native_scene_draw_groups()
vehicle_draw_indices()
validate_vehicle_world_matrix()
apply_vehicle_world_transform()
```

### Non-cumulative guarantee

`apply_vehicle_world_transform()` accepts an immutable
`VehicleObjectGeometry::vertex_bytes` baseline and creates a new transformed
buffer for every call.

This is deliberate.  Step N never consumes the transformed bytes from step
N-1.  Translation, rotation or scale therefore cannot accumulate artificial
frame drift.

### Semantic parity with Phase 584

For semantic-aware SVGP data the native core reuses the established math:

```text
POSITION 200: p' = p * A + t
NORMAL   220: n' = normalize(n * transpose(inverse(A)))
TANGENT  240: t' = normalize(t * A)
TANGENT2 250: t' = normalize(t * A)
```

Singular matrices, non-finite matrices, missing/duplicate POSITION, invalid
FLOAT3 semantic storage and collapsed direction vectors fail closed.

No retail shader constant register is assigned and no shader ABI is changed.

## Regression coverage

Python:

```text
tests/test_native_vehicle_world_transform_script.py
tests/test_native_playable_scene_vulkan_set.py
```

They cover:

- script roundtrip;
- contiguous step enforcement;
- non-finite/non-affine/singular rejection;
- exact `bundle_set.groups` ordering;
- unknown/missing vehicle group rejection;
- Phase 643 emission of `track` followed by `vehicle` from the authoritative
  draw rows.

Native C++ is compiled and executed from:

```text
tests/test_native_vehicle_world_transform_transport_cpp.py
```

The native check proves:

- two different fixed-step translations are independently applied from the same
  object-space baseline;
- the second result is not cumulative;
- a nontrivial affine matrix follows the existing row-vector transform math;
- script parsing preserves matrix translation lanes;
- group parsing selects only explicit vehicle draw indices;
- singular matrices are rejected.

## Negative scope

Phase 646 does **not** prove or claim:

- Process 1 `FUN_00765470 -> FUN_007b2270` BODY-owner continuity;
- positive retail Phase 698/700 BODY0 pose selection;
- BODY0 local frame == BMW MEB/VHF object frame;
- a BODY origin/basis -> final BMW world-matrix mapping;
- dynamic camera follow;
- that a scripted matrix is retail gameplay evidence;
- live Vulkan buffer mutation in `shift_runtime`.

The Phase 645 static VHF transform remains the startup transform until a proven
dynamic producer is supplied.

## Next blocker

After Phase 646 the renderer-side implementation gap is mechanical rather than
semantic:

```text
ready Phase 643 composite scene
  -> object-space baseline for explicit vehicle draws
  -> Phase 646 per-step transform result
  -> remap HOST_VISIBLE|HOST_COHERENT vehicle vertex buffer
  -> render same scene without touching track draws
```

That wiring can be implemented without changing shader constants or inventing a
BODY-to-MEB transform.  Independently, Process 1 still owns the remaining retail
BODY-array owner continuity proof.  Once both sides are ready, the final live
join is reduced to supplying a proven world matrix into this transport.
