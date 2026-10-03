# Phase 643 — native playable scene composition

## Playable-slice blocker reduced

Before this phase the native Vulkan runtime had two independently working draw
paths that could not coexist in one frame:

```text
Silverstone -> SHIFT.NativeSceneVulkanSet/1 -> --scene-set
BMW body    -> SHIFT.BMWVulkanBundleSet/1   -> --bundle-set
```

`shift_runtime` deliberately accepts exactly one geometry source.  Therefore an
already prepared Silverstone scene and an already prepared real BMW draw set
could not form the target:

```text
Silverstone + real vehicle + Vulkan rendering
```

Phase 643 removes that integration blocker without weakening the runtime loader.
The output remains the existing neutral `SHIFT.NativeSceneVulkanSet/1`, so
`shift_runtime --scene-set` and the Phase 585/586 admission ABI stay unchanged.

## Composition path

New module:

```text
src/scene/native_playable_scene_vulkan_set.py
```

produces:

```text
prepared Silverstone NativeSceneVulkanSet children
    + canonical BMW material slice / material-slice set
      -> exact BMW RenderCommand + neutral MEB
      -> genuine SHIFT.VulkanDrawBundle/1 vehicle children
      -> Phase 585 prepare
    -> one ordered SHIFT.NativeSceneVulkanSet/1
    -> SHIFT.NativeSceneVulkanSetPrepare/1
```

The wrapper report is:

```text
SHIFT.NativePlayableSceneVulkanSet/1
```

and the native-consumed files remain:

```text
bundle_set_manifest.json       # SHIFT.NativeSceneVulkanSet/1
bundle_set_prepare.json        # SHIFT.NativeSceneVulkanSetPrepare/1
bundle_set.paths
```

## Track preservation

The input track set must already have both ready contracts:

- `SHIFT.NativeSceneVulkanSet/1`;
- `SHIFT.NativeSceneVulkanSetPrepare/1`.

Every track child manifest is SHA-256 revalidated and its directory is copied
byte-for-byte into the composite root.  Track children are not rebuilt and their
runtime draw provenance is not altered.

## BMW neutral rebuild, not relabelling

The historical BMW path emits `SHIFT.BMWVulkanBundle/1`.  Phase 643 does not
change the `format` string on those manifests.

Instead it goes back to the canonical BMW material slice and rebuilds every
selected body primitive with the existing neutral `build_vulkan_draw_bundle()`
API.  The call explicitly uses:

```text
require_runtime_provenance = false
```

because canonical BMW path+SHA/material admission is resource/static evidence,
not a Silverstone D3D9 runtime draw observation.  The emitted
`SHIFT.VulkanDrawRuntimeProvenanceGate/1` is still present and ready, but records
that runtime provenance was not required for this vehicle resource path.

Exact material DDS data is resolved through the existing BMW BFF provenance and
DDS bridge.  Missing/ambiguous archive entries or SHA drift remain blockers.

## Vehicle renderer identity

Vehicle rows retain an explicit source identity containing:

- canonical BMW body MEB path;
- resolved MEB SHA-256;
- material-slice SHA-256;
- source submesh index.

The stable hash of that identity becomes the neutral scene draw identity for the
vehicle child.  This establishes a durable **renderer vehicle-object identity**
for the later physics transform join without assigning any BODY.

## Transform boundary

The BMW source `RenderCommand.world_matrix` is mandatory.  It is serialized by
the existing neutral builder into `SHIFT.VulkanWorldTransformPacket/1` and then
prepared/executed by the existing Phase 584–586 scene path.

Phase 643 never inserts an identity matrix when the source matrix is missing.

More importantly, the phase does **not** consume:

- `SHIFT.NativeVehicleBodyPoseSelection/1` from Phase 698;
- a persistent BODY snapshot;
- a guessed chassis BODY;
- a BODY-pose-to-renderer matrix convention.

The report therefore keeps:

```text
persistent_BODY_pose_consumed = false
phase698_vehicle_BODY_selection_consumed = false
dynamic_vehicle_world_transform_claimed = false
```

The initial/source BMW transform and the future dynamic physics transform remain
separate contracts.

## Draw ordering

Composite order is deterministic:

```text
all prepared track draws, in original order
then all canonical BMW body draws, in material-slice order
```

Each row records:

```text
source_group = track | vehicle
```

The standard `bundle_set.paths` remains contiguous and relative, so the existing
native scene-set loader needs no new geometry-source mode.

## Remaining blocker after Phase 643

With a ready retail BMW material slice and required DDS/cube resources, the
renderer can now execute Silverstone and the real BMW body in one scene-set.
The next cross-process blocker becomes narrower:

```text
Process 1 proven chassis BODY selection
+ Phase 698 persistent selected BODY pose
+ Phase 643 exact vehicle renderer identity
+ proven BODY pose -> vehicle RenderCommand/SVWT convention
-> dynamic vehicle world transform
```

Process 1 PR #1183 still leaves chassis semantic selection and update-child to
vehicle-base continuity unresolved.  Phase 643 does not bypass either boundary.

## Tests

Focused regressions cover:

- deterministic track-then-vehicle ordering;
- track child manifest SHA tamper rejection;
- missing BMW source world matrix rejection;
- neutral BMW rebuild with runtime provenance explicitly not required;
- no BMW-manifest relabelling;
- no Phase 698/dynamic vehicle pose claim.

No original game execution and no new runtime capture are introduced.
