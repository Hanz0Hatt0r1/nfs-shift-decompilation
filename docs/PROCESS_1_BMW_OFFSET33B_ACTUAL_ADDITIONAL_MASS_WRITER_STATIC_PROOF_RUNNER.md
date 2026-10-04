# Process 1 — one-command BMW actual additional-mass writer proof

## Playable-slice blocker reduced

`SHIFT.BMWOffset33bActualAdditionalMassWriterFrontier/1` bounds the corrected
`actual PhysicsParticipant+0xba0 == embedded Vehicle+0x860` producer search, but
running it manually still required constructing a four-function Ghidra export.

This runner removes that coordination edge.

Contract:

```text
SHIFT.BMWOffset33bActualAdditionalMassWriterStaticProofBundle/1
```

Runner:

```text
tools/ghidra/run_bmw_offset33b_actual_additional_mass_writer_static_proof.py
```

## One targeted export

The runner opens the existing retail Ghidra project through the established
read-only/noanalysis exporter and requests exactly:

```text
FUN_007125e0
FUN_0072ed20
FUN_0079c1c0
FUN_0079bfd0
```

The target set is derived directly from the merged #1256 analyzer's frozen
function inventory. No wider constructor neighborhood is exported.

The single instruction artifact is then consumed by:

```text
SHIFT.BMWOffset33bActualAdditionalMassWriterFrontier/1
```

which proves the `+0x340` actual-participant -> embedded-Vehicle receiver relation
and searches only the corrected `+0xba0/+0x860` target span.

## Decisions

The bundle routes the next proof without manual inspection:

```text
evaluate-direct-writer-value
```

when #1256 finds a direct target writer. The next work is only that writer's
reported dependency slice.

```text
export-same-receiver-forward-callees
```

when the constructor receiver proof is ready but no direct target writer exists.
The emitted same-receiver worklist becomes the exact next targeted export.

```text
resolve-constructor-receiver-proof
```

when the affine receiver relation itself is not yet proven.

No branch promotes a constant-looking STORE root to a numeric value automatically.

## Failure policy

Instruction-export and analyzer failures persist a fail-closed bundle. A valid
instruction artifact is retained when the downstream frontier rejects retail
structure or provenance.

The runner preserves all corrected #1250/#1256 negative gates:

```text
actual_additional_mass_numeric_value_ready = false
BMW_numeric_offset33b_ready = false
BODY0_to_outer_vehicle_root_numeric_matrix_ready = false
BODY0_bind_frame_proof_ready = false
vehicle_world_transform_ready = false
```

The retracted manager-record zero assumption is never consumed.

## Usage

```bash
cd /home/pes/nfs-shift-decompilation

GHIDRA_HOME=/opt/ghidra \
python3 tools/ghidra/run_bmw_offset33b_actual_additional_mass_writer_static_proof.py \
  /home/pes/ghidra_projects/shift \
  shift \
  out/shift_ghidra_database \
  out/bmw_actual_additional_mass_writer_proof
```

Artifacts:

```text
01_actual_additional_mass_constructor_instructions.jsonl
02_actual_additional_mass_writer_frontier.json
bmw_offset33b_actual_additional_mass_writer_static_proof_bundle.json
```

No original-game execution, Wine run, PID attach, or new runtime capture is
required for this stage.
