# Process 1 — player vehicle render-manager indirect dispatch

## Blocker

The shortest playable-slice blocker remains `SHIFT.BMWBody0BindFrameProof/1`.
`SHIFT.PlayerVehicleRenderManagerMethodCa4Access/1` closed the complete 17-direct-callee branch negatively: no targeted direct callee contains a p-code-backed `+0xca4` access whose base is the proven manager entry register.

The positive receiver frontier still contains exactly three independent manager receiver transfers through `CALL EDX`:

```text
FUN_0056bcd0 @ 0x0056bcf2
FUN_0056bcd0 @ 0x0056bd09
FUN_0056bd30 @ 0x0056bd59
```

Those are the remaining bounded first-hop method candidates. Broad caller/callee expansion is not authorized.

## Input

This proof consumes:

1. negative `SHIFT.PlayerVehicleRenderManagerMethodCa4Access/1`;
2. positive `SHIFT.PlayerVehicleRenderManagerReceiverTransferFrontier/2`;
3. the already acquired constructor/writer instruction export containing exactly `FUN_00d36210` and `FUN_0045ef50`;
4. `static_tables.jsonl` from the retail Ghidra database;
5. one new instruction export containing only `FUN_0056bcd0` and `FUN_0056bd30`.

The constructor is revalidated physically:

```text
0x0045ef59  MOV ESI,ECX
...
0x0045ef78  MOV dword ptr [ESI],0xab5644
```

Thus a non-null `DAT_00bc185c` render-manager instance has primary dispatch table pointer `0x00ab5644` at object offset zero on the proven constructor path.

The existing receiver frontier independently proves the same manager pointer reaches each of the three indirect calls in `ECX`, and records the zero-offset object dereferences that load the primary table into `EAX`.

## Contract

`tools/ghidra/analyze_player_vehicle_render_manager_indirect_dispatch.py` emits:

```text
SHIFT.PlayerVehicleRenderManagerIndirectDispatch/1
```

For each frozen callsite the analyzer requires one straight-line physical chain:

```text
proven manager object
  -> MOV EAX,[manager]
  -> MOV EDX,[EAX + aligned_slot]
  -> CALL EDX
```

It rejects a dispatch window containing another call, return, or branch; rejects any EAX/EDX clobber that breaks the chain; and resolves the target only from the exact four-byte retail `.rdata` row at:

```text
0x00ab5644 + aligned_slot
```

No callgraph proximity or guessed class hierarchy is used.

A positive report promotes only:

```text
candidate_global_manager_indirect_dispatch_resolved=true
candidate_global_manager_indirect_method_worklist_ready=true
```

It does **not** promote:

```text
player_vehicle_renderables_field_runtime_access_ready
player_vehicle_renderables_owner_join_ready
outer_vehicle_root_to_VHF_vehicle_root_ready
BODY0_bind_frame_proof_ready
vehicle_world_transform_ready
```

## Retail acquisition

Acquire only the two frozen caller bodies:

```bash
cd /home/pes/nfs-shift-decompilation
git pull

GHIDRA_HOME=/opt/ghidra \
bash tools/ghidra/run_shift_function_instructions.sh \
  /home/pes/ghidra_projects/shift \
  shift \
  SHIFT.exe \
  out/player_vehicle_render_manager_indirect_dispatch_callers.jsonl \
  0x0056bcd0 \
  0x0056bd30
```

Resolve the exact slots:

```bash
python tools/ghidra/analyze_player_vehicle_render_manager_indirect_dispatch.py \
  out/player_vehicle_render_manager_method_ca4_access.json \
  out/player_vehicle_render_manager_receiver_transfer_frontier_v2.json \
  out/player_vehicle_render_manager_constructor_writer_instructions.jsonl \
  out/shift_ghidra_database/static_tables.jsonl \
  out/player_vehicle_render_manager_indirect_dispatch_callers.jsonl \
  --json-out out/player_vehicle_render_manager_indirect_dispatch.json
```

Only `out/player_vehicle_render_manager_indirect_dispatch.json` is needed for the next decision.

## Consumer

If all three dispatches resolve, export only the unique targets in `targeted_instruction_worklist` and test those exact methods for entry-manager `-> +0xca4` access. If resolution fails, the failure identifies the exact slot/callsite blocker; do not broaden to unrelated callgraph neighbors.
