# Process 1 — player vehicle renderables runtime alias

## Playable-slice blocker reduced

The current P1.1 transform-semantic blocker remains the missing exact join:

```text
outer Vehicle / car-body owner
  -> player vehicle renderable owner
  -> SMS root-pose / RenderHierarchy owner
  -> canonical BMW VHF vehicle-root / assembly frame
```

The existing constructor proof establishes:

```text
FUN_0045ef50 receiver + 0xca4
  = allocation labelled mPlayerVehicleRenderables
```

The current discovery surface is now
`SHIFT.PlayerVehicleRenderManagerRootPoseXrefRank/1`, which ranks exact
`DAT_00bc185c` users toward the independently frozen SMS root-pose/world-affine
anchors and explicitly removes the wheel-collision lane from positive render
scoring.

This phase proves only whether the **value loaded from that candidate global**
is physically used as the base of a runtime `+0xca4` access.

## Contract

`tools/ghidra/analyze_player_vehicle_renderables_runtime_alias.py` emits:

```text
SHIFT.PlayerVehicleRenderablesRuntimeAlias/1
```

Accepted rank inputs:

```text
preferred: SHIFT.PlayerVehicleRenderManagerRootPoseXrefRank/1
compatible: SHIFT.PlayerVehicleRenderManagerGlobalXrefRank/1
```

Both must be ready, match the retail SHIFT.exe identity, expose one exact
candidate global and an exact non-empty
`ranking.selected_instruction_export_functions` list. For the preferred
root-pose rank, the analyzer additionally requires:

```text
root_pose_positive_anchor_ranking_ready = true
collision_wheel_LOD_anchor_removed_from_positive_render_score = true
```

The second input is one `SHIFT.GhidraFunctionInstructions/2` file containing
**exactly** the functions selected by that rank artifact. The analyzer requires
structured Ghidra p-code for the field access and reuses the established finite
all-path IA-32 register-provenance engine.

## Positive proof condition

A runtime alias is admitted only when all of the following hold in one selected
function:

1. there is a p-code-backed simple register-relative memory access at offset
   `+0xca4`;
2. immediately before that exact instruction, the base register has exactly one
   all-path origin;
3. that single origin is a memory load from the selected candidate global, for
   example:

```text
MOV ESI,dword ptr [0xbc185c]
...
MOV EAX,dword ptr [ESI + 0xca4]
```

or the equivalent Ghidra `DAT_00bc185c` rendering.

Caller-saved register values remain invalidated across calls. A global load
before an unrelated call does not survive by assumption.

## What a positive result proves

A positive result promotes only:

```text
candidate_global_to_ca4_runtime_field_base_alias_ready = true
player_vehicle_renderables_field_runtime_access_ready   = true
```

The output also records the exact input rank format and whether that rank is the
current root-pose-aware surface. This is provenance metadata only; the rank
format itself is not pointer identity.

## Deliberate non-claims

These gates remain false:

```text
candidate_global_render_manager_class_identity_ready = false
player_vehicle_renderables_owner_join_ready          = false
outer_vehicle_root_to_VHF_vehicle_root_ready          = false
BODY0_bind_frame_proof_ready                          = false
vehicle_world_transform_ready                         = false
```

The analyzer does not promote:

- same field offset to class identity;
- callgraph proximity to pointer identity;
- a `+0xca4` field value to BMW VHF root identity;
- a collection member to a coordinate frame;
- the current root-pose ranking score to a physical owner relation.

## Current end-to-end command

Build the preferred rank and export its exact bounded worklist:

```bash
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
```

No retail game execution or new runtime capture is required.

## Required next join

If the physical global -> `+0xca4` alias is positive, the next bounded question
is:

```text
value loaded from globally sourced receiver +0xca4
  -> physical SMS root-pose / external RenderHierarchy owner transfer?
```

That transfer, not rank proximity, is the next owner proof. Only after the
external hierarchy owner is joined to the canonical BMW VHF root can Process 1
materialize the final frame relation and emit a positive
`SHIFT.BMWBody0BindFrameProof/1` for Process 2.
