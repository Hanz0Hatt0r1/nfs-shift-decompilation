# Process 1 — player vehicle render-manager receiver-transfer frontier

## Playable-slice blocker reduced

Current shortest semantic blocker remains `SHIFT.BMWBody0BindFrameProof/1`.
The positive constructor/writer proof now establishes that every non-null value
sourced from `DAT_00bc185c` is a `FUN_0045ef50` receiver and that the same class
has the source-backed `receiver+0xca4 = mPlayerVehicleRenderables` construction
anchor.

The next unresolved edge is therefore not class identity. It is the physical
runtime receiver transfer:

```text
proven DAT_00bc185c render-manager receiver
  -> called manager method / dispatch
  -> entry receiver in callee
  -> receiver+0xca4 runtime access
  -> mPlayerVehicleRenderables value
  -> SMS / RenderHierarchy owner
  -> BMW VHF root/frame
  -> SHIFT.BMWBody0BindFrameProof/1
```

The old direct `DAT_00bc185c -> +0xca4` branch is already exhaustively negative
across all 80 exact global-xref functions and is not reopened here.

## Contract

`tools/ghidra/build_player_vehicle_render_manager_receiver_transfer_frontier.py`
emits:

```text
SHIFT.PlayerVehicleRenderManagerReceiverTransferFrontier/1
```

It consumes exactly:

1. positive `SHIFT.PlayerVehicleRenderManagerGlobalConstructorIdentity/1`;
2. the same exhaustive current
   `SHIFT.PlayerVehicleRenderManagerRootPoseXrefRank/1`;
3. the exact `SHIFT.GhidraFunctionInstructions/2` export for the selected rank
   worklist.

## Physical proof rule

For each exact `READ` xref to `DAT_00bc185c`, the analyzer requires structured
p-code to identify one tracked destination register whose all-path origin after
the read is exactly the candidate-global memory value. That register is replaced
with a unique taint marker and followed through the existing finite IA-32 CFG
register-provenance engine.

A CALL transfer is admitted only when `ECX` or `EDX` has exactly that one marker
at the callsite. Ambiguous CFG merges are rejected.

Two call classes are emitted:

```text
direct-call-manager-receiver-transfer
indirect-call-manager-receiver-transfer
```

Only direct targets enter `targeted_instruction_worklist.functions`. Indirect
CALL operands are preserved as an unresolved dispatch frontier and are never
promoted to a method identity.

The tool also records simple manager-pointer dereferences, stack pushes and
return-value sinks as supporting physical evidence, without assigning field or
owner semantics.

## Deliberate non-claims

Even a positive frontier keeps all of these gates closed:

```text
player_vehicle_renderables_field_runtime_access_ready = false
player_vehicle_renderables_owner_join_ready           = false
outer_vehicle_root_to_VHF_vehicle_root_ready           = false
BODY0_bind_frame_proof_ready                           = false
vehicle_world_transform_ready                          = false
```

A direct CALL target proves only an exact first-hop callee reached with the
proven manager pointer. It does not prove that callee accesses `+0xca4`, that the
field value is a render owner, or that any hierarchy shares the BMW BODY0 frame.

## Retail command

No new Ghidra export is required for this pass. Reuse the existing exhaustive
80-function rank and instruction export:

```bash
cd /home/pes/nfs-shift-decompilation
git pull

python tools/ghidra/build_player_vehicle_render_manager_receiver_transfer_frontier.py \
  out/player_vehicle_render_manager_global_constructor_identity.json \
  out/player_vehicle_render_manager_root_pose_rank_all_xrefs.json \
  out/player_vehicle_render_manager_root_pose_instructions_all_xrefs.jsonl \
  --json-out out/player_vehicle_render_manager_receiver_transfer_frontier.json
```

If `targeted_instruction_worklist.functions` is non-empty, those exact direct
callees are the only next instruction-export targets. No callers, callees of
callees, or generic callgraph neighbors are added by this artifact.

If the direct worklist is empty but
`candidate_global_manager_indirect_dispatch_frontier_ready=true`, the next task
is bounded vtable/indirect-target resolution for only the recorded CALL sites.

If no exact CALL transfer is found, this branch closes negatively and Process 1
must return to the remaining BODY0 construction/frame provenance frontier rather
than broadening the render-manager callgraph search.
