# S6 — `FUN_007682c0` owner-field base provenance

## Blocker

The exact selected-session 180 Hz timing path is positive through persistent BODY inner execution. The next playable-slice blocker is provider-specific producer/owner provenance. The narrowest current provider boundary is the Phase 696 `FUN_007682c0` delta consumer: its arithmetic is recovered, but the exact record receiving the visible `+0x50` delta remains unresolved.

Existing static evidence can already recover a candidate outer-pass receiver origin such as:

```text
memory:[esi+0x339c]
```

The displacement is interesting because the independent positive retail identity contract proves that the global vehicle base owns the BODY-array owner pointer through field `+0x339c`. A displacement match alone is not object identity, however. The base register of the memory load must first be proven to originate from `FUN_00770e80` entry `ECX` on every relevant path.

## Inputs

Primary authority remains the PC retail build:

```text
SHIFT.exe MD5 705af8b420e5eb1e3834ac43d5533c6b
```

The analysis consumes:

- the ordinary PC Ghidra evidence database;
- `SHIFT.GlobalVehicleBodyOwnerIdentity/1` from `evidence/global_vehicle_body_owner_identity_retail.json`;
- a targeted `SHIFT.GhidraFunctionInstructions/2` export for:
  - `FUN_00770e80`;
  - `FUN_0076d100`;
  - `FUN_00769ef0`;
- the existing first-stage `SHIFT.Fun007682c0AccumulatorDestinationReceiverProvenance/1` logic.

The Xbox 360 recomp may be used later as corroboration or search acceleration, but it is not used to replace the PC receiver proof in this stage.

## Tool

```text
tools/ghidra/analyze_fun_007682c0_owner_field_base_provenance.py
```

Output format:

```text
SHIFT.Fun007682c0OwnerFieldBaseProvenance/1
```

The targeted instruction export can be produced with the existing exporter:

```bash
tools/ghidra/run_export_function_instructions.sh \
  /home/pes/ghidra_projects/shift shift SHIFT.exe \
  out/fun_007682c0_destination_receiver_instructions.jsonl \
  FUN_00770e80 FUN_0076d100 FUN_00769ef0
```

Then run:

```bash
python tools/ghidra/analyze_fun_007682c0_owner_field_base_provenance.py \
  out/shift_ghidra_database \
  out/fun_007682c0_destination_receiver_instructions.jsonl \
  evidence/global_vehicle_body_owner_identity_retail.json \
  --json-out out/fun_007682c0_owner_field_base_provenance.json
```

## Proof rule

For each of the two exact outer physics-pass callsites:

```text
0x00770f8f -> FUN_0076d100
0x00770fbf -> FUN_0076d100
```

this pass finds every reachable simple `MOV` load of `[base+0x339c]` that can reach the callsite and reads the all-path origin of `base` immediately before that load.

A positive owner-field base proof requires:

```text
base origin == entry:ECX
```

for every candidate load on both pass paths. It then composes that physical edge only with the already-proven facts that:

```text
FUN_00770e80 entry ECX = global vehicle base
(global vehicle base + 0x339c) = BODY-array owner pointer field
```

and with the first-stage receiver continuity through:

```text
FUN_0076d100 -> FUN_00769ef0 -> FUN_007682c0
```

A positive result therefore proves only:

```text
FUN_007682c0 receiver = pointer loaded from global vehicle + 0x339c
```

## Deliberate remaining blocker

This stage does **not** equate the BODY-array owner pointer with the selected BMW BODY0 record. The existing identity contract explicitly distinguishes the global vehicle base from the owner pointer, and BMW chassis BODY index `0` is a selection fact rather than proof that the owner pointer itself is that BODY record.

Therefore even a positive report keeps:

```text
FUN_007682c0_receiver_is_retail_BMW_BODY0 = false
owner_pointer_to_exact_delta_destination_record_join_proven = false
FUN_007682c0_delta_consumer_internalization_ready = false
phase696_typed_delta_consumer_must_remain_external = true
```

The next proof must join the owner pointer to the exact record receiving the `+0x50` write using source-backed layout/selection provenance. It must not infer the join from the offset, BODY0 plausibility, or test/runtime fixture choices.

## Regression boundary

`tests/test_ghidra_fun_007682c0_owner_field_base_provenance.py` covers:

- positive `ESI <- entry ECX` plus `[ESI+0x339c]` base provenance;
- rejection when the same displacement is based on `entry:EAX`;
- rejection of a direct outer receiver with no owner-field load;
- strict parsing of only simple exact `+0x339c` memory operands.

No original-game execution or runtime capture is required for this bounded static proof.
