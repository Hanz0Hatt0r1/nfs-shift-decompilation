# Process 1 — `FUN_007682c0` accumulator-destination receiver frontier

## Playable-slice blocker reduced

The deepest native vehicle chain still keeps one typed application boundary
external:

```text
Fun007682c0AccumulatorDeltaConsumer
```

Phase 380 proves the source/machine-visible `FUN_007682c0` behavior reads the
three doubles at `+0x78/+0x80/+0x88` and applies the visible scalar result only
at `+0x50`. Phase 696 narrows that application to one typed scalar delta.
Process 1 #1208 separately proves the retail BMW main/chassis BODY is BODY 0 and
that its BODY-array owner pointer is loaded from global vehicle base field
`+0x339c`.

Those facts do **not** yet prove that the concrete record receiving the
`FUN_007682c0 +0x50` write is the retail BMW chassis BODY0 record.

This phase turns that broad identity question into a finite receiver-provenance
worklist:

```text
FUN_00770e80 entry ECX
  = proven global vehicle base 0x00c13700

0x00770f8f -> FUN_0076d100   pass 0 receiver
0x00770fbf -> FUN_0076d100   pass 1 receiver
0x0076d2c1 -> FUN_00769ef0   pass-tail receiver
0x0076a1e8 -> FUN_007682c0   +0x50 application receiver
```

No original game execution or runtime capture is required.

## Contract

Tool:

```text
tools/ghidra/analyze_fun_007682c0_destination_receiver_provenance.py
```

Output:

```text
SHIFT.Fun007682c0AccumulatorDestinationReceiverProvenance/1
```

Inputs:

1. the ordinary saved retail Ghidra evidence directory (`binary.json`,
   `functions.jsonl`, `callgraph.jsonl`);
2. the committed positive retail `SHIFT.GlobalVehicleBodyOwnerIdentity/1`;
3. one targeted `SHIFT.GhidraFunctionInstructions/2` export containing exactly
   the three caller functions needed for receiver tracing:

```text
FUN_00770e80
FUN_0076d100
FUN_00769ef0
```

The analyzer reuses the finite all-path IA-32 register-provenance engine from
the existing BODY0 callsite and SDF vehicle-assembly receiver proofs.

## Retail anchors frozen by the analyzer

The ordinary database must still match the supplied retail executable:

```text
SHIFT.exe MD5 = 705af8b420e5eb1e3834ac43d5533c6b
```

Function fingerprints:

| Function | Role | mnemonic SHA-256 |
| --- | --- | --- |
| `FUN_00770e80` | outer vehicle update | `509d932c8a3c397f69fe91acecadef2bc148a05237a947c226d9ff039860514e` |
| `FUN_0076d100` | two-pass physics update | `ab1d8a14406c88e02240c03b0a636b7433df72e9dfaec4654746d19e6ba6de5c` |
| `FUN_00769ef0` | recovered pass tail | `1ee3fee50472079154d2029eb4c861b3d1b1eda895347c531316678b7e15d1bf` |
| `FUN_007682c0` | motion-read / `+0x50` application | `f60c733cc0d0b3c755b3104953d1dc1d623d15f33978a6cbe50de7947b7f5d34` |

The four direct call edges above are also mandatory. Fingerprint or callgraph
drift fails closed before any semantic result is produced.

## Existing BODY-owner identity consumed, not re-proved

The analyzer requires the current positive retail composition:

```text
global vehicle base                 = 0x00c13700
BODY-array owner pointer field       = +0x339c
BODY-array owner == global base      = false
retail BMW main/chassis BODY index   = 0
retail BMW main/chassis BODY name    = body
Phase 700 BODY handoff admissible    = true
```

This is `evidence/global_vehicle_body_owner_identity_retail.json`.

The new pass does not reinterpret that proof and does not restore the obsolete
assumption that the BODY-array owner pointer equals the global vehicle pointer.

## Fail-closed receiver semantics

For each direct callsite the analyzer records the complete set of ECX origins on
all reachable paths. A callsite is provenance-resolved only when exactly one
concrete origin remains and it is not unknown/derived.

The two `FUN_00770e80 -> FUN_0076d100` passes are kept separate. Even two fully
resolved receivers cannot be merged if their origins differ.

Cross-function propagation is admitted only through an exact caller-entry ECX
continuity result. Therefore:

```text
pass receiver origin
  + exact FUN_0076d100 entry-ECX continuity
  + exact FUN_00769ef0 entry-ECX continuity
  -> outer-entry-relative FUN_007682c0 receiver origin
```

If either inner link reloads/derives another receiver, the analyzer reports that
local origin and stops the composition instead of guessing its parent object.

## `+0x339c` is a candidate, not a proof

A particularly important fail-closed case is an observed memory origin such as:

```text
memory:[esi+0x339c]
```

The displacement matches the independently proven global-vehicle BODY-owner
field. It is still **not** enough to select BODY0: the base register (`ESI` in
this example) must itself be proven to originate from `FUN_00770e80` entry ECX
on all reachable paths at the load.

The generic origin engine deliberately stops at the memory boundary, so this
phase reports:

```text
owner_field_displacement_candidate_observed = true
receiver_to_retail_BMW_chassis_BODY0_join_proven = false
FUN_007682c0_delta_consumer_internalization_ready = false
```

A future narrow promotion may prove the memory-base provenance. This phase does
not turn a matching displacement into semantic identity.

## Direct-global receiver is also not BODY0

If every link forwards entry ECX unchanged, the result is instead:

```text
FUN_007682c0 receiver = FUN_00770e80 entry ECX = 0x00c13700
```

That is a useful result but cannot be relabelled BODY0 because the positive
retail BODY-owner contract explicitly models the BODY-array owner as a distinct
pointer loaded from global `+0x339c`.

The analyzer therefore reports the exact direct-global chain and keeps the typed
consumer external until this apparent domain distinction is resolved.

## Targeted export command

Using the existing Ghidra project:

```bash
cd /home/pes/nfs-shift-decompilation

GHIDRA_HOME=/opt/ghidra \
bash tools/ghidra/run_shift_function_instructions.sh \
  /home/pes/ghidra_projects/shift shift SHIFT.exe \
  out/fun_007682c0_destination_receiver_instructions.jsonl \
  FUN_00770e80 FUN_0076d100 FUN_00769ef0
```

Then run:

```bash
python3 tools/ghidra/analyze_fun_007682c0_destination_receiver_provenance.py \
  out/shift_ghidra_database \
  out/fun_007682c0_destination_receiver_instructions.jsonl \
  evidence/global_vehicle_body_owner_identity_retail.json \
  --json-out out/fun_007682c0_destination_receiver_provenance.json
```

The command exits `0` when all four callsite receiver origins are deterministic,
even if the final semantic BODY0 join remains blocked. It exits `2` when the
receiver provenance itself is ambiguous or the inputs fail validation.

## Process 2 handoff

The existing Phase 696 API remains authoritative:

```text
Fun007682c0EffectProvider
  -> Fun007682c0AccumulatorEffect
  -> Fun007682c0AccumulatorDeltaConsumer
```

Process 2 may remove the typed delta consumer only after a later proof emits:

```text
FUN_007682c0_accumulator_destination_is_retail_BMW_BODY0 = true
FUN_007682c0_delta_consumer_internalization_ready = true
```

This frontier never emits those flags true by itself.

## Preserved negative claims

This phase does not claim:

- complete `FUN_0076d100` semantics;
- complete `FUN_00769ef0` semantics;
- complete `FUN_007682c0` arithmetic;
- a physical name or unit for `+0x50`;
- global vehicle pointer == BODY-array owner pointer;
- a matching `+0x339c` displacement proves BODY ownership;
- the BODY0/VHF bind-frame relation;
- fixed-step retail scheduling ownership;
- original-game execution or a new runtime capture.

## Blocker-graph effect

Before this phase:

```text
FUN_007682c0 +0x50 destination ownership
  -> broad unknown concrete BODY record
```

After this phase:

```text
FUN_007682c0 +0x50 destination ownership
  -> three targeted instruction functions
  -> four exact direct callsites
  -> finite all-path ECX origins
  -> one explicit semantic join against proven global+0x339c BODY owner / BMW BODY0
```

That is the reusable static infrastructure needed to remove the Phase 696 typed
consumer as soon as the exact receiver origin is available.
