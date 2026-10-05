# Process 1 — player vehicle render-manager method `+0xca4` access proof

## Blocker

The shortest playable-slice blocker remains `SHIFT.BMWBody0BindFrameProof/1`.
`SHIFT.PlayerVehicleRenderManagerReceiverTransferFrontier/2` now proves that the
retail `DAT_00bc185c` render-manager pointer reaches a finite set of direct
callees. The next unresolved edge is physical continuity from the proven call
entry register into the constructor-anchored `+0xca4` field.

## Input

`tools/ghidra/analyze_player_vehicle_render_manager_method_ca4_access.py`
consumes exactly three artifacts:

1. positive `SHIFT.PlayerVehicleRenderManagerGlobalConstructorIdentity/1`;
2. positive `SHIFT.PlayerVehicleRenderManagerReceiverTransferFrontier/2` with a
   direct targeted worklist;
3. `SHIFT.GhidraFunctionInstructions/2` containing exactly that direct worklist.

The constructor proof is required independently so the numeric offset is not
promoted by coincidence. Its source-backed layout anchor is:

```text
FUN_0045ef50 receiver + 0xca4
  = allocation labelled mPlayerVehicleRenderables
```

## Proof rule

For each direct target the receiver frontier records whether the proven manager
pointer crossed the CALL boundary in `ECX` and/or `EDX`.

The analyzer then uses the existing finite all-path IA-32 register-provenance
engine inside the callee. A `+0xca4` access is promoted only when:

```text
callsite proven manager pointer in ECX/EDX
  -> same physical register at direct callee entry
  -> zero or more provenance-preserving register copies
  -> base register of p-code-backed [base + 0xca4]
  -> exactly one all-path origin: entry:ECX or entry:EDX
```

A readable field path requires the access to include a p-code `LOAD`. A
write-only relation is recorded but does not admit the next owner-transfer
frontier.

The output contract is:

```text
SHIFT.PlayerVehicleRenderManagerMethodCa4Access/1
```

A positive readable result promotes only:

```text
candidate_global_manager_method_ca4_access_ready = true
player_vehicle_renderables_field_runtime_access_ready = true
```

It explicitly does **not** promote:

```text
player_vehicle_renderables_owner_join_ready
outer_vehicle_root_to_VHF_vehicle_root_ready
BODY0_bind_frame_proof_ready
vehicle_world_transform_ready
```

## Current retail bounded worklist

The positive v2 receiver frontier produced 17 direct targets, with no callgraph
neighbors added:

```text
0x00441fd0
0x00449630
0x00458760
0x00459140
0x0045abe0
0x0045bfc0
0x0045cc50
0x0045db50
0x0045e110
0x0045f980
0x00462250
0x00462400
0x00467e20
0x00468ed0
0x004695e0
0x00489ad0
0x00493fb0
```

Acquire exactly these callees:

```bash
GHIDRA_HOME=/opt/ghidra \
bash tools/ghidra/run_shift_function_instructions.sh \
  /home/pes/ghidra_projects/shift \
  shift \
  SHIFT.exe \
  out/player_vehicle_render_manager_direct_callee_instructions.jsonl \
  0x00441fd0 \
  0x00449630 \
  0x00458760 \
  0x00459140 \
  0x0045abe0 \
  0x0045bfc0 \
  0x0045cc50 \
  0x0045db50 \
  0x0045e110 \
  0x0045f980 \
  0x00462250 \
  0x00462400 \
  0x00467e20 \
  0x00468ed0 \
  0x004695e0 \
  0x00489ad0 \
  0x00493fb0
```

Then run:

```bash
python tools/ghidra/analyze_player_vehicle_render_manager_method_ca4_access.py \
  out/player_vehicle_render_manager_global_constructor_identity.json \
  out/player_vehicle_render_manager_receiver_transfer_frontier_v2.json \
  out/player_vehicle_render_manager_direct_callee_instructions.jsonl \
  --json-out out/player_vehicle_render_manager_method_ca4_access.json
```

## Consumer

If `player_vehicle_renderables_field_runtime_access_ready=true`, Process 1 stops
expanding the manager-method search and traces only the proven loaded `+0xca4`
value into the SMS/RenderHierarchy owner lane. If no exact entry-pointer read is
found, the 17-target direct-method branch is closed as a bounded negative and
the existing three indirect-dispatch transfers become the next live frontier.
