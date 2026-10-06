# Process 3 — BMW VHF root-frame production scene consumer

## BLOCKER

**Какой конкретный blocker первого playable Linux vertical slice снимает эта работа?**

The production BMW scene path already consumed the positive exact resource join
and already serialized the selected BODY object transform into Vulkan SVWT
packets, but it did not consume the newer positive
`SHIFT.BMWVHFHierarchyRootFrame/1` handoff. Therefore the current path could not
prove that the parser/bootstrap matrix used for the canonical BMW render object
was evaluated under the exact same explicit HIERARCHY Root frame and matrix
convention that Process 1 proved in PR #1323.

This is the Process 3 blocker-swarm shard assigned by
`SHIFT.PlayableSliceBlockerSwarm/1`. It does **not** reopen root extraction.

## INPUT

```text
SHIFT.BMWVehicleRenderModelResourceJoin/1
+
SHIFT.BMWVHFHierarchyRootFrame/1
+
exact primary BMW_M3_E36.bff
+
SHIFT.BMWVHFBodyWorldTransform/1
+
Phase 643 SHIFT.NativeSceneVulkanSet/1
```

The production `build_native_playable_scene_bootstrap()` accepts the positive
root-frame handoff explicitly through `vhf_hierarchy_root_frame`. The existing
`tools/bootstrap_playable_linux_slice.py` caller can supply the same handoff to
the production scene stage through:

```text
SHIFT_BMW_VHF_HIERARCHY_ROOT_FRAME=/path/to/bmw_vhf_hierarchy_root_frame.json
```

When the production BMW render-model join is active, absence of that handoff is
a hard fail-closed blocker. Basename lookup and cockpit substitution remain
forbidden.

## OUTPUT

New contract:

```text
SHIFT.BMWVHFRootFrameSceneConsumer/1
```

implemented by:

```text
src/bmw/bmw_vhf_root_frame_scene_consumer.py
```

The consumer does not adjudicate what the HIERARCHY Root means relative to the
outer executable Vehicle. It validates the already-positive Process 1 handoff
against the exact same admitted VHF payload used by the production renderer and
then proves transport through these boundaries:

```text
positive Process 1 Root frame
        |
        v
exact canonical VHF entry/path/SHA
        |
        v
strict explicit MATRIX parser
        |
        +-- exact Root MatrixNumber + parent chain + world matrix
        |
        +-- canonical BODY OBJECT matrix chain contains Root MatrixNumber
        |
        v
Phase 645 BODY object column-vector world matrix
        |
        | exact transpose
        v
RenderCommand D3D row-vector world matrix
        |
        v
Phase 643 vehicle draw bundle(s)
        |
        v
SHIFT.VulkanWorldTransformPacket/1 bytes for every vehicle draw
```

The strict consumer intentionally differs from the old preview convenience path:
a missing MATRIX record is an error. It may not receive an identity fallback.

After Phase 643 composition the consumer reopens every vehicle child manifest,
SHA-validates the child manifest and SVWT artifact, checks the SVWT header and
convention, and requires its float32 matrix to equal the exact Phase 645 BODY
object matrix under the established D3D row-vector representation.

## GATES_CHANGED

Positive only when the full static resource/render transport is verified:

```text
canonical_BMW_VHF_root_frame_scene_consumer_ready = true
static_vehicle_render_object_frame_ready          = true
```

The following remain false or explicitly required upstream:

```text
outer_vehicle_root_to_VHF_vehicle_root_ready = false
BODY0_bind_frame_proof_ready                 = false
vehicle_world_transform_ready                = false
process2_freshness_gated_live_transform_required = true
```

## LIMITS

This contract does not:

- re-prove or reinterpret `SHIFT.BMWVHFHierarchyRootFrame/1`;
- infer executable ownership from resource hierarchy;
- use visual similarity as proof;
- claim that the static VHF root/object transform is a dynamic vehicle pose;
- publish the outer Vehicle -> VHF semantic relation owned by Process 1;
- treat the Phase 648 transform script as retail motion;
- hide absent physics motion with render-side animation;
- claim camera source/ownership/timing.

Live motion remains:

```text
Process 2 PersistentBmwVehicleWorldTransformState
-> Phase 706 freshness read
-> Phase 649 Vulkan upload
```

and stale/test-only core motion remains inadmissible.

## TESTS

`tests/test_process3_bmw_vhf_root_frame_scene_consumer.py` covers:

- exact positive Root -> BODY object ancestry;
- explicit missing-MATRIX rejection (no preview identity fallback);
- BODY matrix chain not descending from the positive Root;
- exact static BODY object matrix preserved into every vehicle SVWT packet;
- tampered SVWT rejection;
- production bootstrap rejection when the positive root-frame handoff is absent.

## NEXT_OWNER

Process 1 remains the sole owner of the outer Vehicle-root -> exact VHF-root
semantic relation and final BODY0 bind proof. Process 2 remains the owner of
persistent/fresh live vehicle transforms and retail scheduler/control execution.
Process 3 consumes only freshness-gated live matrices after those gates become
positive; this static scene consumer remains the exact resource/bootstrap frame
anchor.
