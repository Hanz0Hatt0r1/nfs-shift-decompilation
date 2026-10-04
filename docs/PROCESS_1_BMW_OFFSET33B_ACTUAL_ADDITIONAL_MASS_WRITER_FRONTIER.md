# Process 1 — BMW `offset33b` actual additional-mass writer frontier

## Playable-slice blocker reduced

PR #1250 corrected the object identity behind the `offset33b` additional-mass term. The HighDetailVehicle path reads the separately allocated PhysicsParticipant object stored in manager `record[0]`, not the `0x1fa0` manager record itself.

The corrected alias is:

```text
actual PhysicsParticipant + 0xba0
== embedded Vehicle + 0x860
```

where the embedded Vehicle starts at `actual participant + 0x340`.

This stage makes the next proof finite and prevents the retracted manager-record zero assumption from re-entering the numeric bind path.

Contract:

```text
SHIFT.BMWOffset33bActualAdditionalMassWriterFrontier/1
```

Analyzer:

```text
tools/ghidra/analyze_bmw_offset33b_actual_additional_mass_writer_frontier.py
```

## Exact constructor chain

The analyzer freezes the retail function fingerprints and direct-call sites for:

```text
FUN_007125e0
  0x0071262b -> FUN_0072ed20

FUN_0072ed20
  0x0072ed57 -> FUN_0079c1c0

FUN_0079c1c0
  0x0079c1e1 -> FUN_0079bfd0
```

The four functions are the only required targeted instruction export:

```text
FUN_007125e0
FUN_0072ed20
FUN_0079c1c0
FUN_0079bfd0
```

## Affine receiver proof

Callgraph adjacency is not enough to establish the object alias. The analyzer performs all-path IA-32 register provenance with a narrow affine extension for `MOV`, simple `LEA`, and register `ADD/SUB` by an immediate.

The embedded Vehicle constructor is admitted only if the physical ECX at `0x0072ed57` is exactly:

```text
FUN_0072ed20 entry ECX + 0x340
```

on every reachable path.

The `FUN_0079c1c0 -> FUN_0079bfd0` base-constructor edge is admitted only if ECX remains exactly the `FUN_0079c1c0` entry receiver.

## Writer search

Only p-code `STORE` operations backed by one simple register-relative machine memory operand are considered.

The exact target spans are:

```text
FUN_0072ed20 receiver + 0xba0 .. +0xba3
FUN_0079c1c0 receiver + 0x860 .. +0x863
FUN_0079bfd0 receiver + 0x860 .. +0x863
```

A target STORE is accepted as a direct writer only when its base-register origin is exactly the current function entry ECX on all reachable paths.

For every accepted writer the report records:

- instruction and memory operand;
- exact displacement and byte overlap;
- base-register origin set;
- structured p-code STORE value dependency slice;
- terminal value roots.

The value is **not** promoted to numeric readiness merely because the slice ends in a constant.

## No direct writer case

If the constructor chain contains no direct target STORE, the report emits only direct calls whose ECX is exactly the current constructor receiver. This becomes the bounded next targeted-export worklist.

No unrelated constructor callees are expanded.

## Usage

```bash
GHIDRA_HOME=/opt/ghidra \
bash tools/ghidra/run_shift_function_instructions.sh \
  /home/pes/ghidra_projects/shift \
  shift \
  SHIFT.exe \
  out/bmw_actual_additional_mass_constructor_instructions.jsonl \
  FUN_007125e0 FUN_0072ed20 FUN_0079c1c0 FUN_0079bfd0

python3 tools/ghidra/analyze_bmw_offset33b_actual_additional_mass_writer_frontier.py \
  out/shift_ghidra_database \
  out/bmw_actual_additional_mass_constructor_instructions.jsonl \
  --json-out out/bmw_offset33b_actual_additional_mass_writer_frontier.json
```

## Deliberate non-claims

This stage never revives:

```text
SHIFT.BMWOffset33bAdditionalMassBootstrapZero/1
```

and keeps all of these false:

```text
actual_additional_mass_numeric_value_ready
BMW_numeric_offset33b_ready
BODY0_to_outer_vehicle_root_numeric_matrix_ready
BODY0_bind_frame_proof_ready
vehicle_world_transform_ready
```

The next proof is either exact evaluation of a discovered writer value slice or a second targeted instruction export containing only the same-receiver forwarded callees emitted by this report. No runtime witness is required yet.
