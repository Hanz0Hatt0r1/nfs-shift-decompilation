# Process 1 — outer Vehicle render-root delta provenance

## BLOCKER

**Какой конкретный blocker первого playable Linux vertical slice снимает эта работа?**

`SHIFT.BMWBody0BindFrameProof/1` is blocked on the exact outer Vehicle-root ->
canonical BMW VHF vehicle-root relation.  The merged
`SHIFT.OuterVehicleRenderSnapshotAffineBridge/1` has already reduced that edge
to one setup-produced local translation:

```text
P_snapshot = P_outer + R_outer * delta_local

delta_local = outerVehicle[+0x19c,+0x1a0,+0x1a4]
producer    = FUN_00795d60
```

The remaining semantic join must prove what those three values represent with
respect to the canonical BMW VHF `HIERARCHY` root.  Callgraph proximity, matching
numbers, helper names and visual agreement are not admissible ownership/frame
proof.

## INPUT

The analyzer requires:

- retail `SHIFT.GhidraEvidenceDatabase/1` for `SHIFT.exe`, MD5
  `705af8b420e5eb1e3834ac43d5533c6b`;
- the merged `SHIFT.OuterVehicleRenderSnapshotAffineBridge/1` artifact;
- exactly one targeted `SHIFT.GhidraFunctionInstructions/2` row for
  `FUN_00795d60` (`0x00795d60`, size `8797`, `__fastcall`, exact mnemonic
  fingerprint).

The targeted export is static and read-only; it does not execute the game and is
not a runtime capture:

```bash
GHIDRA_HOME=/opt/ghidra \
bash tools/ghidra/run_shift_function_instructions.sh \
  /home/pes/ghidra_projects/shift \
  shift \
  SHIFT.exe \
  out/outer_vehicle_render_root_delta_fun_00795d60_instructions.jsonl \
  FUN_00795d60
```

## OUTPUT

`tools/ghidra/analyze_outer_vehicle_render_root_delta_provenance.py` emits:

```text
SHIFT.OuterVehicleRenderRootDeltaProvenance/1
```

For every p-code `STORE` overlapping `+0x19c..+0x1a7`, it records:

- exact machine instruction and memory operand;
- store width and touched delta field bytes;
- all-path origin of the target base register;
- whether the target base is exactly function-entry `ECX`;
- backward structured-pcode value slice;
- terminal value roots and root kinds.

A positive `render_root_delta_store_provenance_ready` requires all 12 bytes of
the three float fields to be covered by stores whose base is exactly entry
`ECX`, with no unresolved delta-looking complex target operand.

Run it with:

```bash
python3 tools/ghidra/analyze_outer_vehicle_render_root_delta_provenance.py \
  out/shift_ghidra_database \
  out/outer_vehicle_render_root_delta_fun_00795d60_instructions.jsonl \
  --json-out out/outer_vehicle_render_root_delta_provenance.json
```

## CONSUMER

The consumer is the next bounded Process 1 proof:

```text
exact terminal value roots for +0x19c/+0x1a0/+0x1a4
  -> canonical BMW VHF HIERARCHY Root/resource-frame semantics
  -> prove outer Vehicle-root == VHF vehicle-root
     OR prove exact fixed affine delta
```

Only after that relation and the BMW numeric `offset33b` are both available may
Process 1 compose the numeric BODY0-local -> VHF vehicle-root matrix and emit a
positive `SHIFT.BMWBody0BindFrameProof/1`.

## Explicit limits

This contract deliberately keeps the following gates false:

```text
outer_vehicle_root_to_VHF_vehicle_root_ready         = false
outer_vehicle_root_to_VHF_fixed_affine_delta_ready   = false
BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready = false
BODY0_bind_frame_proof_ready                         = false
vehicle_world_transform_ready                        = false
```

It also does not infer semantics from recent direct calls.  Those calls are
preserved only as local context around a proven store; they are not treated as
producer/owner identity without value-flow proof.

No new runtime capture is requested by this phase.
