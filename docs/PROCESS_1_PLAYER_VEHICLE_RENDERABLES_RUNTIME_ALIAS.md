# Process 1 — player vehicle renderables runtime alias

## Playable-slice blocker reduced

The remaining transform-semantic blocker is still the missing exact join:

```text
outer Vehicle / car-body visual owner
  -> player vehicle renderable owner
  -> canonical BMW VHF vehicle-root / assembly frame
```

The previous two Process 1 stages make the next evidence finite:

- `FUN_0045ef50` independently proves the constructor layout relation
  `render-manager receiver + 0xca4 = allocation labelled mPlayerVehicleRenderables`;
- `SHIFT.PlayerVehicleRenderManagerGlobalXrefRank/1` reduces the candidate
  `DAT_00bc185c` users to a bounded targeted instruction-export worklist.

The missing mechanical step was proving whether the **value loaded from that
candidate global** is actually used as the base of a runtime `+0xca4` access.
This phase automates exactly that step.

## Contract

`tools/ghidra/analyze_player_vehicle_renderables_runtime_alias.py` emits:

```text
SHIFT.PlayerVehicleRenderablesRuntimeAlias/1
```

Inputs:

1. a ready `SHIFT.PlayerVehicleRenderManagerGlobalXrefRank/1` artifact;
2. one `SHIFT.GhidraFunctionInstructions/2` file containing exactly the
   functions selected by `selected_instruction_export_functions`.

The analyzer requires structured Ghidra p-code for the field access and reuses
the established finite all-path IA-32 register-provenance engine.

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

The pass does **not** assume that a caller-saved register survives calls. For
example:

```text
MOV ECX,[DAT_00bc185c]
CALL something
MOV EAX,[ECX+0xca4]
```

is rejected as an exact alias unless independent machine flow restores the
candidate-global value into `ECX`.

## What a positive result proves

A positive result promotes only these physical facts:

```text
candidate_global_to_ca4_runtime_field_base_alias_ready = true
player_vehicle_renderables_field_runtime_access_ready   = true
```

Combined with the independent constructor anchor, this establishes a concrete
runtime use of the same `+0xca4` layout slot by a receiver value loaded from the
candidate global.

It deliberately does **not** prove that offset coincidence alone makes the
candidate global an instance of the constructor's class.

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
- a decompiler parameter name to ABI truth.

## End-to-end commands after the global xref export

First rank the candidate global users:

```bash
python tools/ghidra/rank_player_vehicle_render_manager_global_refs.py \
  out/shift_ghidra_database \
  out/player_vehicle_render_manager_global_refs.jsonl \
  --json-out out/player_vehicle_render_manager_global_xref_rank.json
```

Read `selected_instruction_export_functions` from that artifact and export those
functions with `run_shift_function_instructions.sh`. Then run:

```bash
python tools/ghidra/analyze_player_vehicle_renderables_runtime_alias.py \
  out/player_vehicle_render_manager_global_xref_rank.json \
  out/player_vehicle_render_manager_selected_instructions.jsonl \
  --json-out out/player_vehicle_renderables_runtime_alias.json
```

No retail game execution or new runtime capture is required.

## Required next join

If the physical global -> `+0xca4` alias is positive, the next bounded question
becomes:

```text
value loaded from globally sourced receiver +0xca4
  -> exact HDVehicle / car-body / visual-owner pointer transfer?
```

Only that pointer/value transfer can promote the two render-side frontiers to the
same runtime owner. VHF hierarchy/root identity or a fixed affine relation is a
separate proof after that.
