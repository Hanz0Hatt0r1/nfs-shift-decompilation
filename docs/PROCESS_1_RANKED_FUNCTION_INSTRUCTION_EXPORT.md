# Process 1 — bounded function-instruction export

## Playable-slice blocker reduced

The current Process 1 blocker is the source-backed owner/frame join from the
outer Vehicle root into the canonical BMW VHF vehicle-root / assembly frame.
Three bounded frontiers already emit exact instruction worklists for that join:

- `SHIFT.PlayerVehicleRenderManagerRootPoseXrefRank/1` is the current preferred
  render-manager ranking surface and points at the independently frozen SMS
  root-pose/world-affine lane;
- `SHIFT.PlayerVehicleRenderManagerGlobalXrefRank/1` is the older compatible
  render-manager rank artifact;
- `SHIFT.VehicleRenderRootPoseTransportFrontier/1` bounds the independent SMS
  root-pose/world-affine transport path directly.

The remaining orchestration risk was manually copying one of those exact lists
into `run_shift_function_instructions.sh`. That is unnecessary scope drift in an
otherwise bounded static proof.

`tools/ghidra/run_ranked_function_instructions.py` removes that manual step. The
input artifact is authoritative and the wrapper forwards **exactly** its selected
function list to the existing targeted Ghidra exporter.

## Supported artifacts

### Current render-manager root-pose rank

```text
SHIFT.PlayerVehicleRenderManagerRootPoseXrefRank/1
  -> ranking.selected_instruction_export_functions
```

This is the preferred rank input for the current blocker. Its positive anchors
are the SMS participant/render-hierarchy/world-affine path; the wheel-collision
`FUN_007a3d60` lane is not used as a positive render signal.

### Legacy-compatible render-manager xref rank

```text
SHIFT.PlayerVehicleRenderManagerGlobalXrefRank/1
  -> ranking.selected_instruction_export_functions
```

Both rank formats are hash/identity validated and enforce their
`selected_instruction_export_limit` when present. Supporting the older format is
compatibility only; it does not restore the obsolete collision-biased ranking as
the preferred frontier.

### SMS root-pose transport frontier

```text
SHIFT.VehicleRenderRootPoseTransportFrontier/1
  -> targeted_instruction_worklist.functions
```

The nested worklist must explicitly request
`SHIFT.GhidraFunctionInstructions/2`.

## Safety properties

The wrapper fails before Ghidra when:

- the artifact is not ready or has an unsupported format;
- SHIFT.exe retail identity differs from MD5
  `705af8b420e5eb1e3834ac43d5533c6b`;
- the selected worklist is empty or contains duplicate normalized addresses;
- a rank worklist exceeds its own declared export limit;
- any worklist exceeds the wrapper safety cap (64 by default).

It never adds neighboring functions, callers, callees, or guessed targets.

## Current render-manager command

Build the current root-pose-aware rank with the exact `DAT_00bc185c` reference
artifact, then export only its selected functions:

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

That instruction artifact is the bounded input for the next physical
pointer/value-provenance join from a selected render-manager user into the SMS
root-pose owner.

## SMS root-pose command

First build the static frontier:

```bash
python tools/ghidra/build_vehicle_render_root_pose_transport_frontier.py \
  out/shift_ghidra_database \
  --json-out out/vehicle_render_root_pose_transport_frontier.json
```

Then export its exact worklist without copying addresses by hand:

```bash
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
render_manager_owner_to_SMS_root_pose_owner_join_ready = false
outer_vehicle_root_to_VHF_vehicle_root_ready           = false
BODY0_bind_frame_proof_ready                            = false
vehicle_world_transform_ready                           = false
```

The immediate consumer is the next Process 1 instruction-level owner/provenance
proof. Once that proof joins the concrete SMS/GraphicsEngine hierarchy owner to
the canonical BMW VHF root, the result feeds the final
`SHIFT.BMWBody0BindFrameProof/1` handoff to Process 2.
