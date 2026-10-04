# Process 1 — outer Vehicle transform sink receiver provenance

## Playable-slice blocker reduced

`SHIFT.OuterVehicleVHFRootRelationFrontier/1` bounds the remaining
outer-`Vehicle`-root -> VHF-root proof to the complete direct fan-out of
`FUN_007927c0`. Before tracing transform stack values, the pointer domains at
that fan-out must be separated so work is not spent reverse-engineering sinks
that do not own assembly state.

Contract:

```text
SHIFT.OuterVehicleTransformSinkReceiverProvenance/1
```

Analyzer:

```text
tools/ghidra/analyze_outer_vehicle_transform_sink_receiver_provenance.py
```

## Exact physical lanes

The analyzer evaluates ECX on every reachable machine path at these boundaries:

```text
0x0079280e -> FUN_007876e0   __thiscall receiver
0x00792828 -> FUN_007afb60   __thiscall receiver
0x00792884 -> FUN_00787160   __fastcall first argument
0x007928e3 -> FUN_007633b0   __thiscall receiver, proven HDVehicle physics control
0x007928f0 -> FUN_007ac2f0   __thiscall receiver
```

`FUN_007633b0` is the control lane because the existing symbolic bind proof
independently establishes its HDVehicle chassis-transform role. The other
receivers are compared with that physical ECX origin, but matching expressions
are not promoted to pointer equality, owner equality, or frame identity.

The two no-`this` helpers in the outer setter fan-out are not included in this
receiver pass. They can be reopened later only if a surviving transform value
slice terminates in them.

## Targeted export

Only the outer setter is required for this stage:

```bash
GHIDRA_HOME=/opt/ghidra \
bash tools/ghidra/run_shift_function_instructions.sh \
  /home/pes/ghidra_projects/shift \
  shift \
  SHIFT.exe \
  out/outer_vehicle_setter_instructions.jsonl \
  FUN_007927c0
```

Then run:

```bash
python3 tools/ghidra/analyze_outer_vehicle_transform_sink_receiver_provenance.py \
  out/outer_vehicle_vhf_root_relation_frontier.json \
  out/outer_vehicle_setter_instructions.jsonl \
  --json-out out/outer_vehicle_transform_sink_receiver_provenance.json
```

The all-path IA-32 register provenance engine is the same engine already used by
the BODY0 bind callsite and BMW SDF assembly receiver proofs.

## Output and narrowing

For every sink the report records:

- exact callsite/callee/ABI role;
- all reachable ECX origin expressions;
- whether the origin is deterministic;
- whether ECX is exactly the outer setter entry ECX;
- whether the origin-expression set matches the proven HDVehicle sink;
- a lexical audit window, explicitly marked as non-path-proof.

The report also groups identical origin-expression sets and emits only the three
anonymous `__thiscall` sinks as `next_owner_candidates`. `FUN_00787160` remains
separate because fastcall ECX is an argument, not a `this` receiver.

## Deliberate non-claims

Even a deterministic matching memory origin does **not** prove that two loads
produce the same pointer value at different points in time. Therefore this stage
keeps:

```text
outer_vehicle_root_to_VHF_vehicle_root_ready         = false
outer_vehicle_root_to_VHF_fixed_affine_delta_ready   = false
BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready = false
BODY0_bind_frame_proof_ready                         = false
vehicle_world_transform_ready                        = false
```

It also refuses to promote:

- matching origin expressions to pointer equality;
- matching origin expressions to frame identity;
- fastcall ECX to a `this` receiver;
- lexical adjacency to path proof;
- callgraph adjacency to VHF owner identity.

## Next proof

For each deterministic surviving `__thiscall` receiver domain, inspect only that
callee's concrete writes/forwards and trace its owner-producing edge. The first
candidate that joins to the canonical BMW VHF hierarchy loader/owner becomes the
outer Vehicle-root/VHF-root relation target. Only after this owner narrowing is
complete should stack position/orientation provenance be evaluated.
