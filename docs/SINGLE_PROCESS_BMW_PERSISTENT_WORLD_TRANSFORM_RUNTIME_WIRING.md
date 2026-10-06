# Single-process S4 — persistent BMW world-transform runtime wiring

## BLOCKER

**Какой конкретный blocker первого playable Linux vertical slice снимает эта работа?**

S4 closes `BMW-persistent-world-transform-admission`: the now-positive
`SHIFT.BMWBody0BindFrameProof/1` must become a current persistent BMW vehicle
world transform in the production fixed-step continuation, before the existing
freshness-gated Vulkan sink runs.

## INPUT

Already-positive contracts and infrastructure:

- `SHIFT.BMWBody0BindFrameProof/1`;
- `SHIFT.NativeBMWBody0BindFrameProofPacket/1`;
- `SHIFT.NativeBMWBody0BindFrameRuntimeAdmission/1`;
- positive retail BMW BODY0 owner identity;
- persistent BODY0 pose/snapshot freshness transport;
- `SHIFT.PersistentBMWVehicleWorldTransform/1` commit/read path;
- prepared vehicle-child `SHIFT.VulkanWorldTransformPacket/1` static transforms;
- Phase 715 freshness-gated Vulkan consumer.

No new retail frame identity is inferred in S4.

## OUTPUT

`native_runtime/include/shift_bmw_persistent_world_transform_runtime_wiring.hpp`
implements:

```text
positive BBFP admission before fixed_step
-> native_state.fixed_step(intent)
-> resolve prepared BMW vehicle-child SVWT bind
-> commit_retail_bmw_vehicle_world_transform(...)
-> publish_persistent_bmw_vehicle_world_transform_for_render(...)
-> Phase 715 freshness-gated live vehicle upload
```

The fixed-step injection now executes that sequence in exactly this order.

Machine-readable checkpoint:

```text
SHIFT.BMWPersistentWorldTransformRuntimeWiring/1
```

at:

```text
evidence/bmw_persistent_world_transform_runtime_wiring.json
```

## Static scene bind provenance

The dynamic Phase 715 reapply uses each vehicle child's raw `geometry.svpk`, so
the static body-MEB -> VHF-root transform must remain in the composed world
matrix. S4 therefore consumes the exact `world_transform.svwt` already admitted
and executed for the prepared native scene child.

The packet must be exact SVWT v1 / convention 1 / 64-byte matrix payload and a
finite nonsingular D3D row-vector affine matrix.

The playable BMW body may produce multiple Vulkan draws because the canonical
BODY MEB has multiple submeshes. S4 never picks one draw arbitrarily. It requires
all entries labelled `vehicle` by `bundle_set.groups` to carry byte-identical
SVWT matrices. Any disagreement fails closed.

## Freshness

The post-step commit reuses the existing Phase 706 transaction and retains:

```text
body_index == 0
source_runtime_body_count
source_pose_snapshot_generation
source_explicit_update_count
source_origin
source_basis
commit_generation
```

Phase 715 reads the same published persistent state and already rejects stale
source generations/counts and reused commit generations.

## GATES_CHANGED

Positive after this wiring is admitted:

```text
vehicle_world_transform_ready = true
```

Still false:

```text
retail_cadence_admitted       = false
retail_control_chain_complete = false
retail_camera_follow_ready    = false
```

A host frame rate, host `1/60`, or the existence of repeated fixed-step calls is
not retail scheduler/cadence evidence.

## LIMITS

- No original-game execution or new runtime capture.
- No static scene matrix is relabelled as dynamic pose; it is only the proven
  static VHF bind factor consumed with the current BODY0 runtime pose.
- No test transform script is required by the S4 production path.
- S4 does not prove retail scheduler/cadence ownership.
- S4 does not complete input/control or camera-follow semantics.
- The BBFP environment seam remains the already-built positive-only admission
  boundary; profile/launcher packaging may supply it later without changing the
  recovered transform semantics.

## TESTS

Native regression covers:

- exact vehicle draw-group selection;
- multi-submesh SVWT consensus;
- disagreement rejection;
- SVWT ABI drift rejection;
- missing vehicle draw rejection;
- inert behavior without positive BBFP admission;
- positive BBFP -> current BODY0 persistent commit generation 1;
- retained snapshot/update freshness provenance;
- current-state re-read after publication.

Python regression locks call order:

```text
admission / fixed_step
< S4 commit+publish
< Phase715
< Phase648 test-script regression hook
```

## NEXT_STEP

S5 is now the shortest blocker: prove and consume retail outer-update
scheduler/cadence ownership. Keep host loop frequency and host `1/60` excluded
from retail evidence.
