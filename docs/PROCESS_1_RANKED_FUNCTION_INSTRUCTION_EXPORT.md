# Process 1 — bounded function-instruction export

## Playable-slice blocker reduced

Two current Process 1 frontiers already emit finite instruction worklists:

- `SHIFT.PlayerVehicleRenderManagerGlobalXrefRank/1` reduces candidate
  render-manager global xrefs;
- `SHIFT.VehicleRenderRootPoseTransportFrontier/1` bounds the independent SMS
  root-pose/world-affine transport path.

The remaining orchestration risk was manually copying either list into
`run_shift_function_instructions.sh`. That is unnecessary scope-drift in an
otherwise exact static proof.

`tools/ghidra/run_ranked_function_instructions.py` removes that manual step. The
input artifact is authoritative and the wrapper forwards **exactly** its selected
function list to the existing targeted Ghidra exporter.

## Supported artifacts

### Render-manager xref rank

```text
SHIFT.PlayerVehicleRenderManagerGlobalXrefRank/1
  -> ranking.selected_instruction_export_functions
```

The wrapper also enforces the rank artifact's
`selected_instruction_export_limit` when present.

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

## Render-manager command

```bash
cd /home/pes/nfs-shift-decompilation

GHIDRA_HOME=/opt/ghidra \
python tools/ghidra/run_ranked_function_instructions.py \
  out/player_vehicle_render_manager_global_xref_rank.json \
  /home/pes/ghidra_projects/shift \
  shift \
  out/player_vehicle_render_manager_selected_instructions.jsonl
```

The result feeds `analyze_player_vehicle_renderables_runtime_alias.py`.

## SMS root-pose command

First build the static frontier:

```bash
python tools/ghidra/build_vehicle_render_root_pose_transport_frontier.py \
  out/shift_ghidra_database \
  --json-out out/vehicle_render_root_pose_transport_frontier.json
```

Then export its exact ten-function worklist without copying addresses by hand:

```bash
GHIDRA_HOME=/opt/ghidra \
python tools/ghidra/run_ranked_function_instructions.py \
  out/vehicle_render_root_pose_transport_frontier.json \
  /home/pes/ghidra_projects/shift \
  shift \
  out/vehicle_render_root_pose_transport_instructions.jsonl
```

Use `--dry-run` with either artifact to print the normalized exact function list
and shell command without starting Ghidra.

## Boundary

This wrapper is orchestration only. It does not promote ranking, callgraph
frontiers, instruction-export membership, or successful Ghidra execution to
pointer/class/frame identity. All world-transform gates remain controlled by the
downstream instruction-level proof artifacts.
