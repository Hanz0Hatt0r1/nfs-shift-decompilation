# Process 1 — player-vehicle-renderables first-hop owner-transfer frontier

## Blocker

The playable-slice critical path remains P1.1:

```text
positive SHIFT.BMWBody0BindFrameProof/1
```

The current unresolved frame/owner edge is narrower:

```text
outer Vehicle / car-body owner
  -> proven render-manager runtime +0xca4 value
  -> SMS/GraphicsEngine RenderHierarchy owner
  -> canonical BMW VHF vehicle-root / assembly frame
```

`SHIFT.PlayerVehicleRenderablesRuntimeAlias/1` already proves a physical runtime
alias between the candidate `DAT_00bc185c` receiver and its `+0xca4` field
access. It deliberately does not prove where the **value loaded from that
field** goes.

This phase extracts only the first physical transfer sinks of that loaded value.
It is not another callgraph ranker and does not classify unrelated functions.

## INPUT

`tools/ghidra/build_player_vehicle_renderables_owner_transfer_frontier.py`
requires all three inputs:

1. positive `SHIFT.PlayerVehicleRenderablesRuntimeAlias/1`;
2. the exact current `SHIFT.PlayerVehicleRenderManagerRootPoseXrefRank/1` that
   selected the instruction worklist;
3. one `SHIFT.GhidraFunctionInstructions/2` export containing exactly that
   selected worklist.

The runtime-alias artifact must itself record:

```text
input_rank.format          = SHIFT.PlayerVehicleRenderManagerRootPoseXrefRank/1
input_rank.root_pose_aware_rank = true
candidate_global_to_ca4_runtime_field_base_alias_ready = true
player_vehicle_renderables_field_runtime_access_ready   = true
```

Legacy collision-biased rank provenance is rejected for this new frontier.

## OUTPUT

The analyzer emits:

```text
SHIFT.PlayerVehicleRenderablesOwnerTransferFrontier/1
```

For every positive `+0xca4` alias, it admits a taint seed only when the access is
a simple pointer-sized `MOV` read into one tracked IA-32 register. It then reuses
the existing finite all-path register-provenance engine and emits only exact
physical sinks reachable from that read:

- direct-call transfer in `ECX`;
- direct-call transfer in `EDX`;
- dereference through the exact field value;
- store of the exact field value to memory;
- `PUSH` of the exact field value;
- the exact field value still present in `EAX` at a return boundary.

A value that becomes ambiguous at a CFG merge is not promoted. `EAX`, `ECX` and
`EDX` are invalidated across calls by the existing IA-32 caller-saved rule.
Indirect call targets are never guessed.

### Exact continuation worklist

Only direct callsites where `ECX` or `EDX` contains exactly the tainted field
value contribute to:

```text
targeted_instruction_worklist.functions
```

Targets are deduplicated, bounded, and no neighbors/callers/callees are added.
The register position is recorded as physical machine evidence only; this
artifact does not assert a semantic ABI parameter role for the callee.

When only a store/dereference/push/return sink exists, the frontier remains
useful but the direct-callee worklist stays empty. The next proof must continue
from that exact sink instead of expanding the callgraph heuristically.

## Positive frontier condition

The contract uses `ready=true` only when at least one exact physical first-hop
sink survives all-path provenance from a seedable `+0xca4` pointer load.

That opens only:

```text
player_vehicle_renderables_first_hop_transfer_frontier_ready = true
```

If an exact direct callee receives the value in `ECX` or `EDX`, it additionally
opens:

```text
player_vehicle_renderables_direct_transfer_worklist_ready = true
```

Neither condition is semantic owner identity.

## Gates that remain closed

This stage always keeps:

```text
player_vehicle_renderables_owner_join_ready                 = false
sms_vehicle_world_affine_RenderHierarchy_owner_join_ready    = false
outer_vehicle_root_to_VHF_vehicle_root_ready                 = false
BODY0_bind_frame_proof_ready                                 = false
vehicle_world_transform_ready                                = false
```

It does not promote:

- root-pose rank proximity to pointer identity;
- `ECX`/`EDX` register position to a semantic callee parameter;
- a memory destination to an object identity;
- a dereference offset to field semantics;
- a first-hop recipient to RenderHierarchy/VHF ownership;
- any first-hop transfer to frame equality or affine-frame relation.

## Regression properties

The dedicated regression suite proves that the extractor:

- follows an exact loaded field value through register copies into a direct
  `ECX` call transfer;
- deduplicates repeated exact direct targets;
- rejects an `ECX` value that differs across CFG paths;
- loses caller-saved provenance across an intervening call;
- records an exact memory store without inventing destination ownership;
- rejects runtime-alias evidence rooted in the legacy rank;
- fails closed when the exact direct-target worklist exceeds its cap.

Synthetic fixtures validate only the analysis infrastructure. They do not make
a retail-semantic gate positive.

## Retail command chain

The actual retail proof requires the targeted Ghidra instruction export from the
current rank:

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

python tools/ghidra/analyze_player_vehicle_renderables_runtime_alias.py \
  out/player_vehicle_render_manager_root_pose_rank.json \
  out/player_vehicle_render_manager_root_pose_instructions.jsonl \
  --json-out out/player_vehicle_renderables_runtime_alias.json

python tools/ghidra/build_player_vehicle_renderables_owner_transfer_frontier.py \
  out/player_vehicle_renderables_runtime_alias.json \
  out/player_vehicle_render_manager_root_pose_rank.json \
  out/player_vehicle_render_manager_root_pose_instructions.jsonl \
  --json-out out/player_vehicle_renderables_owner_transfer_frontier.json
```

## CONSUMER

The immediate consumer is the next Process 1 pointer/value-provenance proof:

```text
exact first-hop recipient/store consumer
  -> SMS/GraphicsEngine RenderHierarchy owner
  -> canonical BMW VHF vehicle-root / fixed affine relation
  -> SHIFT.BMWBody0BindFrameProof/1
```

Only a positive source-backed owner/frame join may be handed to Process 2 as
retail vehicle-world-transform semantics.
