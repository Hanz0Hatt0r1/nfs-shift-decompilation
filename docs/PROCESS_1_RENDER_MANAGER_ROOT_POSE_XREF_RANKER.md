# Process 1 — render-manager root-pose xref ranking

## Blocker reduced

The playable Linux slice still needs a source-backed owner join between the
persistent vehicle world transform and the canonical BMW VHF hierarchy/root.
The first render-manager global-xref ranker used `FUN_007a3d60` as a positive
`vehicle-visual/LOD` anchor.  Subsequent decompiler inspection showed that this
function constructs wheel collision convexes (`COLLISION_CONVEX_%s_%x`) with the
`rubber tyre` material.  Treating `_WHEEL_*_LODA` proximity as render evidence
therefore biases the search toward a physics/collision lane.

`rank_player_vehicle_render_manager_root_pose_refs.py` keeps that function as a
negative/discovery control but removes it from positive render scoring.

## Positive anchors

The v2 ranking surface uses exact retail fingerprints for:

```text
FUN_0045ef50  render-manager + mPlayerVehicleRenderables constructor anchor
FUN_007ac4d0  car-body/CHASSIS boundary
FUN_004848bc  SMS participant render tick
FUN_004ae150  vehicle RenderHierarchy node-local update lane
FUN_00480700  SMS vehicle world-affine consumer
FUN_004a8c20  vehicle render-model world-point consumer
```

The SMS anchors are shared with
`SHIFT.VehicleRenderRootPoseTransportFrontier/1`, so the ranker cannot silently
drift away from the independently frozen root-pose transport neighborhood.

## Negative control

`FUN_007a3d60` remains fingerprint-gated and its directed callgraph distance is
reported for every candidate, but:

```text
collision_proximity_used_as_positive_render_signal = false
```

This is deliberately conservative.  The current collision classification is
supported by decompiler evidence; a dedicated instruction-level negative proof
is still required before the old visual-hierarchy branch is formally retired.

## Run

Use the same exact `DAT_00bc185c` global-reference export as the previous
ranker:

```bash
python tools/ghidra/rank_player_vehicle_render_manager_root_pose_refs.py \
  out/shift_ghidra_database \
  out/player_vehicle_render_manager_global_refs.jsonl \
  --json-out out/player_vehicle_render_manager_root_pose_rank.json
```

The selected instruction-export functions are now ranked toward the SMS
world-pose/render lane instead of the wheel collision lane.

## Proof boundary

A high rank remains discovery evidence only.  The report leaves these gates
closed:

```text
render_manager_owner_to_SMS_root_pose_owner_join_ready = false
outer_vehicle_root_to_VHF_vehicle_root_ready           = false
BODY0_bind_frame_proof_ready                            = false
vehicle_world_transform_ready                           = false
```

The next promotion requires physical pointer/value provenance from one selected
`DAT_00bc185c` user into the SMS root-pose owner and then the external
GraphicsEngine/RenderHierarchy owner receiving the world affine.
