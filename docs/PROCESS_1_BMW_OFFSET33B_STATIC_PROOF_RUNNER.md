# Process 1 — one-command BMW `offset33b` static proof runner

## Playable-slice blocker reduced

The BMW world-transform blocker is now bounded by
`SHIFT.BMWOffset33bStoreProvenance/1`, but obtaining that report still required
manually running the targeted Ghidra exporter and then invoking the analyzer.
This runner removes that coordination step and makes the exact existing Ghidra
project the only external static input.

Contract:

```text
SHIFT.BMWOffset33bStaticProofBundle/1
```

Runner:

```text
tools/ghidra/run_bmw_offset33b_static_proof.py
```

## One command

```bash
cd /home/pes/nfs-shift-decompilation

python3 tools/ghidra/run_bmw_offset33b_static_proof.py \
  /home/pes/ghidra_projects/shift \
  shift \
  out/shift_ghidra_database \
  out/bmw_offset33b_static_proof \
  --ghidra-home /opt/ghidra \
  --timeout-seconds 300
```

The runner opens the already analyzed `SHIFT.exe` from the Ghidra project through
`run_shift_function_instructions.sh`. That shell runner uses `-readOnly` and
`-noanalysis`, isolates the Java exporter in a temporary script directory, and
validates the emitted `SHIFT.GhidraFunctionInstructions/2` before returning.
Only one target is requested:

```text
FUN_0076b280
```

The original game is not executed.

## Persisted artifacts

The output directory contains:

```text
01_fun_0076b280_instructions.jsonl
02_bmw_offset33b_store_provenance.json
bmw_offset33b_static_proof_bundle.json
```

A Ghidra/export failure writes a failure bundle. If export succeeds but the
static analyzer fails closed on retail drift or malformed evidence, the validated
instruction export is preserved for audit and repair.

## Automatic next-step classification

A completed bundle classifies the exact value frontier without making the BMW
numbers ready:

- `constant-root-evaluation` — all terminal roots are constants/address-space
  selectors; next work is an exact p-code evaluator for only the observed
  operations;
- `resource-or-init-memory-join` — a terminal root is external/memory; next work
  is to join the exact load to the already materialized BMW SDF/init path;
- `register-or-helper-return-provenance` — unresolved register/unique state
  remains; the bundle includes nearby direct helper targets so only the narrow
  return boundary needs tracing;
- `store-frontier-incomplete` — the three HDVehicle fields are not yet fully
  covered by exact entry-ECX STORE targets.

This means a single retail run selects the next Process 1 proof instead of
requiring manual inspection of the whole 7796-byte function.

## Deliberate non-claims

The bundle always keeps these false unless a later dedicated numeric proof closes
them:

```text
BMW_numeric_offset33b_ready                      = false
BODY0_to_outer_vehicle_root_numeric_matrix_ready = false
BODY0_bind_frame_proof_ready                     = false
vehicle_world_transform_ready                    = false
```

It does not reinterpret raw constant varnodes as IEEE-754 doubles, invent CALL
returns or x87 state, infer resource-field semantics from an address, or execute
the original game.

## Why this is on the critical path

After the recent resource-driven handoff, the exact BMW SDF is already available
directly from `SHIFT.OfflineRuntimeBootstrap/1`. The symbolic BODY0 -> outer
Vehicle-root relation is also already proven. Therefore the remaining numeric
translation proof should consume the precise `FUN_0076b280` value roots and the
exact admitted BMW resource/init data, not reopen broad reverse-engineering
searches.
