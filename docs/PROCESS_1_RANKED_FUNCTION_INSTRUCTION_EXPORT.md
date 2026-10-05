# Process 1 — bounded function-instruction export

## Playable-slice blocker reduced

The current Process 1 blocker is the source-backed owner/frame join from the
outer Vehicle / HighDetailVehicle assembly domain into the canonical BMW VHF
vehicle-root / assembly frame. Several bounded frontiers emit exact instruction
worklists for that join:

- `SHIFT.PlayerVehicleRenderManagerRootPoseXrefRank/1` — current preferred
  render-manager ranking surface;
- `SHIFT.PlayerVehicleRenderManagerGlobalXrefRank/1` — legacy-compatible rank;
- `SHIFT.VehicleRenderRootPoseTransportFrontier/1` — independent SMS
  root-pose/world-affine path;
- `SHIFT.OuterVehicleVHFRootRelationFrontier/1` — source-labelled outer Vehicle
  spawn/setter fan-out;
- `SHIFT.VehicleDescriptorPhysicsRenderOwnerFrontier/1` — exact direct callers
  of HighDetailVehicle::Init after the paired VehicleDetails render/physics
  property reflection is proven.

`tools/ghidra/run_ranked_function_instructions.py` removes the manual address
copy step. The input artifact is authoritative and the wrapper forwards
**exactly** its selected function list to the existing targeted Ghidra exporter.

## Supported artifacts

### Current render-manager root-pose rank

```text
SHIFT.PlayerVehicleRenderManagerRootPoseXrefRank/1
  -> ranking.selected_instruction_export_functions
```

Its positive anchors are the SMS participant/render-hierarchy/world-affine path;
the wheel-collision `FUN_007a3d60` lane is not used as a positive render signal.

### Legacy-compatible render-manager xref rank

```text
SHIFT.PlayerVehicleRenderManagerGlobalXrefRank/1
  -> ranking.selected_instruction_export_functions
```

Both rank formats are hash/identity validated and enforce their
`selected_instruction_export_limit` when present.

### SMS root-pose transport frontier

```text
SHIFT.VehicleRenderRootPoseTransportFrontier/1
  -> targeted_instruction_worklist.functions
```

### Outer Vehicle/VHF root relation frontier

```text
SHIFT.OuterVehicleVHFRootRelationFrontier/1
  -> targeted_instruction_worklist.functions
```

### VehicleDetails physics/render owner frontier

```text
SHIFT.VehicleDescriptorPhysicsRenderOwnerFrontier/1
  -> targeted_instruction_worklist.functions
```

The last frontier currently emits only the complete direct caller set of
source-backed `HighDetailVehicle::Init` (`FUN_0076df50`). Its own
`targeted_instruction_worklist.max_functions` is enforced in addition to the
wrapper-wide cap.

Every nested frontier worklist must explicitly request
`SHIFT.GhidraFunctionInstructions/2`.

## Safety properties

The wrapper fails before Ghidra when:

- the artifact is not ready or has an unsupported format;
- `SHIFT.exe` retail identity differs from MD5
  `705af8b420e5eb1e3834ac43d5533c6b`;
- the selected worklist is empty or contains duplicate normalized addresses;
- a rank or frontier worklist exceeds its declared limit when present;
- any worklist exceeds the wrapper safety cap (64 by default).

It never adds neighboring functions, callers, callees, or guessed targets.

## VehicleDetails physics/render command

After building the frontier, export only its exact HighDetailVehicle::Init
callers:

```bash
GHIDRA_HOME=/opt/ghidra \
python tools/ghidra/run_ranked_function_instructions.py \
  out/vehicle_descriptor_physics_render_owner_frontier.json \
  /home/pes/ghidra_projects/shift \
  shift \
  out/vehicle_descriptor_physics_render_init_callers.jsonl
```

The instruction artifact is for physical second-argument provenance only. A
common `VehicleDetails` class or matching resource family is not coordinate-frame
identity.

## Current render-manager command

```bash
cd /home/pes/nfs-shift-decompilation

python tools/ghidra/rank_player_vehicle_render_manager_root_pose_refs.py \
  out/shift_ghidra_database \
  out/player_vehicle_render_manager_global_refs.jsonl \
  --json-out out/player_vehicle_render_manager_root_pose_rank.json

GHIDRA_HOME=/opt/ghidra \
python tools/ghidra/run_ranked_function_instructions.py \
  out/player_vehicle_render_manager_root_pose_rank.json \
  /home/pes/ghidra_projects/shift \
  shift \
  out/player_vehicle_render_manager_root_pose_instructions.jsonl
```

## SMS root-pose command

```bash
python tools/ghidra/build_vehicle_render_root_pose_transport_frontier.py \
  out/shift_ghidra_database \
  --json-out out/vehicle_render_root_pose_transport_frontier.json

GHIDRA_HOME=/opt/ghidra \
python tools/ghidra/run_ranked_function_instructions.py \
  out/vehicle_render_root_pose_transport_frontier.json \
  /home/pes/ghidra_projects/shift \
  shift \
  out/vehicle_render_root_pose_transport_instructions.jsonl
```

Use `--dry-run` with any supported artifact to print the normalized exact
function list and shell command without starting Ghidra.

## Boundary and handoff

This wrapper is orchestration only. It does not promote ranking, callgraph
frontiers, instruction-export membership, or successful Ghidra execution to
pointer/class/frame identity. In particular it keeps:

```text
outer_vehicle_root_to_VHF_vehicle_root_ready = false
BODY0_bind_frame_proof_ready                  = false
vehicle_world_transform_ready                 = false
```

The immediate consumer is the next Process 1 instruction-level owner/value
provenance proof. Once the physics/render assembly relation is physically joined
and any intervening affine delta is proven, the result feeds the final
`SHIFT.BMWBody0BindFrameProof/1` handoff to Process 2.
