# Process 1 — ranked function-instruction export

## Playable-slice blocker reduced

`SHIFT.PlayerVehicleRenderManagerGlobalXrefRank/1` already reduces the candidate
render-manager global's xrefs to a bounded function worklist. The remaining
manual step was copying that list into `run_shift_function_instructions.sh`.
That creates avoidable scope-drift risk in the exact owner/frame proof.

`tools/ghidra/run_ranked_function_instructions.py` removes that manual step. The
rank artifact is authoritative: the wrapper validates it and forwards **exactly**
`selected_instruction_export_functions` to the existing targeted Ghidra
instruction exporter.

## Safety properties

The wrapper fails before Ghidra when:

- the rank artifact is not a ready
  `SHIFT.PlayerVehicleRenderManagerGlobalXrefRank/1`;
- SHIFT.exe retail identity differs from MD5
  `705af8b420e5eb1e3834ac43d5533c6b`;
- the selected worklist is empty or contains duplicate normalized addresses;
- the worklist exceeds its own declared export limit;
- the worklist exceeds the wrapper safety cap (64 by default).

It never adds neighboring functions, callers, callees, or guessed targets.

## Command

After generating:

```text
out/player_vehicle_render_manager_global_xref_rank.json
```

run:

```bash
cd /home/pes/nfs-shift-decompilation

GHIDRA_HOME=/opt/ghidra \
python tools/ghidra/run_ranked_function_instructions.py \
  out/player_vehicle_render_manager_global_xref_rank.json \
  /home/pes/ghidra_projects/shift \
  shift \
  out/player_vehicle_render_manager_selected_instructions.jsonl
```

Use `--dry-run` to print the normalized exact function list and shell command
without starting Ghidra.

The resulting JSONL can be fed directly into
`analyze_player_vehicle_renderables_runtime_alias.py` once that pass is present
on the branch/main being tested.

## Boundary

This wrapper is orchestration only. It does not promote callgraph ranking,
global references, instruction export membership, or successful Ghidra
execution to pointer/class/frame identity. All existing world-transform gates
remain controlled by the downstream proof artifacts.
