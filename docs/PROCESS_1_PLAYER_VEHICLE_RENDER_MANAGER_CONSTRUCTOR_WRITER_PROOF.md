# Process 1 — player vehicle render-manager constructor/writer proof

## Playable-slice blocker reduced

The current Process 1 critical path remains:

```text
outer Vehicle / render owner
  -> canonical BMW VHF vehicle-root/frame
  -> SHIFT.BMWBody0BindFrameProof/1
  -> Process 2 persistent retail BODY0 update
```

The previous candidate-global branch asked whether an exact user of
`DAT_00bc185c` also performed a physical `receiver+0xca4` access.  The retail
search has now been exhausted across all 80 functions containing an exact xref
to the global:

```text
selected_function_count                    = 80
pcode_backed_ca4_access_count              = 0
exact_candidate_global_value_alias_count   = 0
```

That negative result closes the direct global-xref -> `+0xca4` branch.  It does
not invalidate `DAT_00bc185c` as the render-manager candidate because a manager
method may access the field after the receiver has crossed a call boundary.

The next independent question is therefore class identity:

```text
what exact object can be written to DAT_00bc185c?
```

## New physical writer lane

The exact global-reference rank contains 116 references in 80 functions but
only two `WRITE` references.  Both are in `FUN_00d36210`:

```text
0x00d362ec  MOV [0x00bc185c],EAX
0x00d362f3  MOV dword ptr [0x00bc185c],ESI
```

The targeted instruction export shows this non-null lane:

```text
0x00d36224  XOR ESI,ESI
...
0x00d362b9  PUSH 0x46e0
0x00d362be  CALL FUN_008868c0
...
0x00d362d3  CMP EAX,ESI
0x00d362d5  JZ 0x00d362f3
0x00d362d7  MOV ECX,EAX
0x00d362d9  CALL FUN_0045ef50
0x00d362de  JMP 0x00d362ec
0x00d362ec  MOV [0x00bc185c],EAX
```

and the alternate path stores the already-zeroed `ESI`:

```text
0x00d362f3  MOV dword ptr [0x00bc185c],ESI
```

This is stronger than callgraph proximity: the allocation result is the
physical receiver supplied to the exact constructor anchor whose result is then
written to the candidate global.

## Constructor anchor retained

The existing source-backed anchor for `FUN_0045ef50` remains:

```text
0x0045ef59  MOV ESI,ECX

0x0045f191  PUSH 0xab55a4   ; "mPlayerVehicleRenderables"
0x0045f196  PUSH 0x400
0x0045f1a1  CALL FUN_00695e30
0x0045f1a8  CALL FUN_00695f10
0x0045f1af  CALL FUN_0068a700
0x0045f1bf  MOV [ESI+0xca4],EAX
```

Ghidra may render a plain immediate address without leading zeroes, for example
`0xab55a4` instead of the frozen canonical spelling `0x00ab55a4`.  The analyzer
therefore compares only plain `0x...` immediate operands numerically.  Register,
memory, field-layout and control-flow operands remain structurally fail-closed;
this normalization cannot turn `[0xbc185c]` into `[0x00bc185c]` or otherwise
hide a receiver/layout drift.

The new proof does not assume a C++ constructor ABI from convention alone.  It
runs the established finite all-path IA-32 register-provenance engine over the
full `FUN_0045ef50` instruction export and admits class identity only if every
reachable `RET` carries exactly:

```text
EAX origin = entry:ECX
```

Thus the caller-side store can be joined to the same receiver that entered the
constructor.

## Contract

`tools/ghidra/analyze_player_vehicle_render_manager_constructor_writer.py`
emits:

```text
SHIFT.PlayerVehicleRenderManagerGlobalConstructorIdentity/1
```

A positive result promotes only:

```text
candidate_global_render_manager_class_identity_ready       = true
candidate_global_non_null_FUN_0045ef50_receiver_ready      = true
constructor_player_vehicle_renderables_layout_anchor_ready = true
```

The claim is specifically:

> every source-backed write to `DAT_00bc185c` is either zero or the receiver
> returned by `FUN_0045ef50`; therefore every non-null value sourced from this
> global has the constructor/layout identity proven for `FUN_0045ef50`.

## Required inputs

The analyzer fail-closes unless all three inputs agree with the frozen retail
identity `SHIFT.exe` MD5 `705af8b420e5eb1e3834ac43d5533c6b`:

1. exhaustive negative `SHIFT.PlayerVehicleRenderablesRuntimeAlias/1` from all
   80 exact xref functions;
2. exhaustive `SHIFT.PlayerVehicleRenderManagerRootPoseXrefRank/1` whose 80
   selected functions contain exactly the two known global writes;
3. `SHIFT.GhidraFunctionInstructions/2` containing exactly:

```text
0x00d36210
0x0045ef50
```

## Retail acquisition

Export only the writer and constructor bodies:

```bash
cd /home/pes/nfs-shift-decompilation

GHIDRA_HOME=/opt/ghidra \
bash tools/ghidra/run_shift_function_instructions.sh \
  /home/pes/ghidra_projects/shift \
  shift \
  SHIFT.exe \
  out/player_vehicle_render_manager_constructor_writer_instructions.jsonl \
  0x00d36210 \
  0x0045ef50
```

Then run the proof:

```bash
python tools/ghidra/analyze_player_vehicle_render_manager_constructor_writer.py \
  out/player_vehicle_renderables_runtime_alias_all_xrefs.json \
  out/player_vehicle_render_manager_root_pose_rank_all_xrefs.json \
  out/player_vehicle_render_manager_constructor_writer_instructions.jsonl \
  --json-out out/player_vehicle_render_manager_global_constructor_identity.json
```

No retail game execution or runtime capture is required.

## Deliberate non-claims

Even a positive class-identity result keeps these gates closed:

```text
candidate_global_to_ca4_runtime_field_base_alias_ready = false
player_vehicle_renderables_field_runtime_access_ready   = false
player_vehicle_renderables_owner_join_ready             = false
outer_vehicle_root_to_VHF_vehicle_root_ready             = false
BODY0_bind_frame_proof_ready                              = false
vehicle_world_transform_ready                             = false
```

The proof does **not** promote:

- a field offset coincidence to class identity;
- callgraph proximity to pointer identity;
- null to a class instance;
- the `mPlayerVehicleRenderables` collection itself to the BMW VHF root;
- collection membership to coordinate-frame identity.

## Next finite frontier after a positive result

Once `DAT_00bc185c` is a proven render-manager receiver, the next bounded static
question becomes:

```text
proven DAT_00bc185c receiver
  -> direct manager-method call / physical receiver transfer
  -> receiver+0xca4 access inside that method
  -> mPlayerVehicleRenderables value transfer
  -> SMS / external RenderHierarchy owner
```

That is the next admissible owner proof.  The exhausted direct-global `+0xca4`
search must not be reopened unless independent evidence changes the candidate
writer/class identity.
