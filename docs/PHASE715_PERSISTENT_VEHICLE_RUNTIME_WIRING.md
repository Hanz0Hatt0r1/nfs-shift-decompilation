# Phase 715 — persistent vehicle transform runtime wiring

## Blocker reduced

**Which concrete blocker of the first playable Linux vertical slice does this work remove?**

Phase 649 already proves the fail-closed sink:

```text
current SHIFT.PersistentBMWVehicleWorldTransform/1
-> Phase 706 freshness validation
-> wait all in-flight Vulkan fences
-> SHIFT.LiveVehicleVertexBufferUpload/1
```

However, the real `shift_runtime` fixed-step frame attachment still reached vehicle
Vulkan mutation only through the Phase 648
`SHIFT_NATIVE_VEHICLE_WORLD_TRANSFORM_SCRIPT` regression source. The Phase 649
consumer existed only as a reusable API and standalone regression.

Phase 715 removes that remaining Process 3 mechanical gap. It attaches an
already-committed Phase 706 persistent state to the same real fixed-step point and
then delegates the actual upload to Phase 649.

```text
Process 2 publishes committed Phase 706 state
        |
        v
shift_runtime fixed_step attachment
        |
        v
SHIFT.PersistentVehicleRuntimeWiring/1
        |
        v
SHIFT.PersistentVehicleVulkanUpload/1
        |
        v
freshness gate -> Vulkan vehicle vertex upload -> runtime.frame()
```

## BLOCKER / INPUT / OUTPUT / CONSUMER

```text
BLOCKER
  P3.2 real shift_runtime did not consume the Phase 706 persistent transform;
  only the explicit Phase 648 test-motion script reached the frame-loop upload.

INPUT
  SHIFT.PersistentBMWVehicleWorldTransform/1
  SHIFT.PersistentVehicleVulkanUpload/1
  SHIFT.RuntimeVehicleVulkanWiring/1 scene/draw attachment infrastructure

OUTPUT
  SHIFT.PersistentVehicleRuntimeWiring/1
  + monotonic Phase 706 publication API
  + real shift_runtime fixed-step attachment
  + Phase 649 freshness-before-GPU preservation

CONSUMER
  Process 2 current-world-transform publication. Once the canonical Process 1/2
  semantic gates make a current Phase 706 state available, no new Process 3
  matrix convention, scene selection, or Vulkan upload layer is required.
```

## Publication boundary

`publish_persistent_bmw_vehicle_world_transform_for_render(...)` accepts only a
ready Phase 706 state with a positive commit generation. After the first
publication, commit generations must increase monotonically.

The publisher does **not**:

- select BODY0;
- commit or compose a vehicle matrix;
- execute or schedule physics;
- infer retail cadence;
- manufacture a bind frame;
- derive camera state.

Those remain upstream Process 1/2 responsibilities.

Until any Phase 706 state is published, the Phase 715 hook is inert. Therefore
P3.1 Silverstone + exact BMW composition keeps its established behavior while the
upstream current-transform gate remains blocked.

## Fail-closed frame behavior

Once publication starts, every Phase 715 fixed-step hook requires a commit newer
than the last successfully uploaded commit. Reusing the previous generation is
rejected before Phase 649 and before GPU access.

For a new generation Phase 715 delegates to
`upload_current_bmw_vehicle_world_transform_to_vulkan(...)`. Phase 649 performs
the Phase 706 current-source validation before fence waits or Vulkan memory
mutation, so stale BODY pose generation/provenance remains fail-closed.

The persistent producer and the Phase 648 explicit transform script are mutually
exclusive. If `SHIFT_NATIVE_VEHICLE_WORLD_TRANSFORM_SCRIPT` is present after a
persistent state has been published, Phase 715 rejects the frame before the
Phase 648 script hook can mutate Vulkan memory.

## Exact scene attachment reused

Phase 715 does not add a second scene loader or identify the BMW heuristically.
It reuses the established Phase 648 helpers for:

```text
bundle_set.groups
bundle_set.paths
semantic SVGP v3 immutable object-space geometry
```

Vehicle draw selection still comes from the authoritative `vehicle` draw group.
Track Vulkan memory remains outside the upload set.

## Regression and CI

Coverage:

```text
native_runtime/tests/persistent_vehicle_runtime_wiring_check.cpp
tests/test_phase715_persistent_vehicle_runtime_wiring.py
.github/workflows/process-3-phase715-persistent-runtime-wiring.yml
```

The real Vulkan regression proves:

1. the hook is inert before Process 2 publication;
2. a current published Phase 706 generation updates only vehicle memory;
3. an unrefreshed generation is rejected with no GPU mutation;
4. a newer generation is accepted;
5. Phase 706 stale-source validation is preserved before GPU mutation;
6. duplicate publication is rejected;
7. simultaneous persistent and Phase 648 script producers are rejected before
   GPU mutation.

The CI also builds the actual `shift_runtime` target so the forced fixed-step
attachment is compile-checked, not only the standalone regression wrapper.

## Remaining blocker / handoff

Phase 715 does not make the current retail vehicle world transform positive. The
canonical upstream gates remain unchanged: Process 1 must provide the positive
BODY0 bind/frame and scheduling/producer proofs required by Process 2, and
Process 2 must commit a fresh current Phase 706 transform at the admitted update
boundary.

The Process 3 renderer-side mechanical consumer is now ready for that handoff.
No test-only transform script is required by this persistent sink, and no retail
transform producer is claimed by Process 3.
