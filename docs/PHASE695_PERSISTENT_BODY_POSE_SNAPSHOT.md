# Phase 695 — persistent BODY pose snapshot transport

## Playable-slice blocker reduced

The Phase 694 runtime carries persistent retail-shaped BODY records across
complete explicit outer updates, but their proven pose-bearing lanes remain
available only by manually decoding the opaque `0x170` byte buffer.

Static/source-backed BODY integration evidence already proves two persistent
lanes inside each record:

```text
origin  +0x00/+0x08/+0x10   f64 x3
basis   +0xd4..+0xf4         f32 x9
```

Phase 695 makes those exact lanes a typed persistent runtime output:

```text
successful explicit outer update
  -> final persistent BODY bytes
  -> exact BODY-record decode
  -> finite origin/basis validation
  -> commit BODY bytes + typed snapshots together
```

This is reusable infrastructure for the future identity join:

```text
proven vehicle/concrete-object identity
  -> proven BODY index/ownership
  -> Phase 695 BODY pose snapshot
  -> proven vehicle/world transform mapping
  -> scene/camera/render transport
```

The missing identity and transform mappings are not inferred here.

## Native contract

New format:

```text
SHIFT.NativePersistentBodyPoseSnapshot/1
```

Files:

```text
native_runtime/include/shift_persistent_body_pose_snapshot.hpp
native_runtime/src/persistent_body_pose_snapshot.cpp
```

Each snapshot contains only:

```text
body_index
origin : existing BodyFrameIntegrationVector3d (f64 x3)
basis  : existing ConstraintRefreshFrame3f (f32 x9)
```

The decoder delegates record interpretation to the existing
`decode_fun_007bab70_body_record()` adapter. It does not reinterpret or convert
the proven field storage.

## No transform promotion

A Phase 695 snapshot is a **BODY pose snapshot**, not a vehicle transform.

This phase does not prove:

- which BODY index belongs to the retail vehicle object;
- that a BODY origin is the scene object's world translation;
- the renderer's matrix row/column convention for the BODY basis;
- a basis transpose, handedness conversion or axis remap;
- the scene node/draw instance that should consume the snapshot;
- a camera follow target;
- a BODY-to-resource or BODY-to-renderer identity join.

Accordingly Phase 695 performs no basis transpose/remap and does not write any
`world_transform.svwt`, Vulkan push constant or scene transform.

## Process 1 boundary

The latest Process 1 merge at the start of this phase is PR #1167,
`SHIFT.VehicleReturnedAllocationPointerReturnProvenance/1`.

It narrows the exact returned-EAX provenance frontier on the vehicle creation
side, but explicitly keeps allocation semantics and same-runtime-object identity
unproven. Therefore Phase 695 does not select a vehicle BODY index from that
create-side evidence.

The first future join that may promote a BODY pose toward a vehicle transform
must require independent Process 1 proof of the concrete runtime-object/BODY
relationship.

## Process 3 boundary

While Phase 695 was being implemented, Process 3 merged PR #1171. Phase 639 now
owns a unified fail-closed resource→renderer vertical-slice bootstrap and passes
the exact runtime bootstrap produced in the same invocation into the renderer
evidence pipeline.

That is the correct future Process 3 transport surface, but PR #1171 explicitly
remains orchestration: renderer-evidence completion is not runtime render
admission and it does not establish a physics BODY→scene-object identity.

Phase 695 therefore stops before that unified renderer boundary while providing
the typed physics-side payload a future proven BODY/object/scene identity join
can consume.

## Transactional persistent state

`ExplicitOuterUpdateRuntimeState` now stores:

```text
body_bytes
body_pose_snapshots
body_pose_snapshot_generation
```

Initialization:

1. validates BODY byte cardinality;
2. decodes all BODY snapshots into temporary state;
3. rejects non-finite origin/basis values;
4. only then commits initial BODY bytes and snapshots;
5. sets `body_pose_snapshot_generation = 0`.

Every successful explicit outer-update path now performs the same sequence on its
returned BODY bytes before mutating persistent state. After commit:

```text
body_pose_snapshot_generation == explicit_update_count
```

A failed participant/workspace gate, physics provider, solver path, malformed
BODY result, or pose decode leaves the previously committed BODY bytes and pose
snapshots unchanged.

## Fail-closed decoder

`decode_persistent_body_pose_snapshots()` rejects:

- `body_count == 0`;
- multiplication/cardinality overflow;
- a byte buffer whose size is not exactly `body_count * 0x170`;
- NaN/Inf in any of the three f64 origin components;
- NaN/Inf in any of the nine f32 basis components.

It does not normalize an imperfect basis. Such a change would introduce new
behavior not present in the proven record transport.

## Reference oracle

Python decoder:

```text
src/physics/persistent_body_pose_snapshot_runtime.py
```

Regression:

```text
tests/test_persistent_body_pose_snapshot_runtime.py
```

The oracle decodes exactly the same little-endian f64/f32 lanes and freezes the
negative scope:

```text
body_to_vehicle_identity_proven = false
vehicle_world_transform_proven = false
renderer_transport_enabled = false
basis_transpose_or_remap = false
```

## Native regression

```text
shift_runtime_persistent_body_pose_runtime_state_check
```

The regression reuses the full Phase 691/694 two-BODY, six-scalar solver fixture
and the deepest current Phase 694 explicit path.

It verifies:

- initialization produces two typed snapshots at generation 0;
- the initial BODY 0 origin is `(1, 2, 3)`;
- after the first complete two-half-step outer update BODY 0 origin is
  `(3.125, 4.65625, 6.1875)`;
- each snapshot exactly matches an independent decode of the same committed raw
  BODY record;
- a second outer update advances both the raw BODY state and the typed pose;
- snapshot generation advances exactly with `explicit_update_count`;
- the zero-rotation scalar fixture preserves the raw basis path without a Phase
  695 transform conversion;
- participant rejection preserves committed bytes, pose and generation;
- a NaN origin is rejected by the standalone decoder and by runtime
  initialization before partial state is committed;
- explicit updates still do not increment `physics.fixed_step`.

## Scheduling and machine-scalar guards

Phase 695 does not modify physics scheduling. The Phase 694 outer update remains
explicit and does not run from `NativeRuntimeState::fixed_step()`.

It also does not change any machine-scalar boundary. In particular it does not
use host `sqrt`, `sin` or `cos` to replace unresolved retail x87/scalar
production.

## Next blocker

After Phase 695, the transform-side blocker is narrower:

```text
persistent physics
  -> typed BODY origin+basis                         closed
  -> concrete vehicle/object -> BODY identity       blocked on Process 1
  -> BODY basis/origin -> vehicle world transform   blocked on Process 1
  -> vehicle transform -> unified scene/render handoff blocked on proven identity transport
```

If Process 1 closes the concrete object/BODY mapping, Process 2 can consume that
proof directly and hand a proven transform toward Process 3's unified renderer
surface without first inventing a byte-buffer decoding layer.

No original game execution or new runtime capture is used.
