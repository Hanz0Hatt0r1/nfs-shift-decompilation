# Phase 738 — FUN_007618f0 second-argument provenance

Phase 737 closed the two pointer-backed vector inputs used by `FUN_007618f0`: `HDVehicle+0x820` and `HDVehicle+0x12a0` are the selected BMW FL/FR wheel BODY pointers, so their current origins can be read from persistent BODY indices 3 and 4.

The only unresolved inputs of the already-native Phase 728 local-sample formula are now the fields read from the explicit second source object:

- `source+0x338` — f64;
- `source+0x918` — inline f64 vec3.

Phase 738 does **not** assign a class or physical name to that object from those offsets. It adds a reproducible PC-retail static proof pipeline for the actual callsite argument.

## Stage 1 — exact direct-caller worklist

`build_fun_007618f0_second_arg_worklist.py` consumes the standard `ShiftEvidenceExporter` database:

- `binary.json`;
- `functions.jsonl`;
- `callgraph.jsonl`.

It requires the retail executable identity `705af8b420e5eb1e3834ac43d5533c6b`, finds only non-indirect callgraph edges whose target is `0x007618f0`, and emits the unique direct caller function addresses plus exact callsites.

Callgraph membership is discovery evidence only. It is not treated as semantic ownership.

## Stage 2 — physical stack-argument provenance

`analyze_fun_007618f0_second_arg_provenance.py` consumes targeted `SHIFT.GhidraFunctionInstructions/2` rows for those callers.

For every exact direct callsite it:

1. validates that the instruction is still a direct `CALL` to `FUN_007618f0`;
2. requires the immediately preceding instruction to be a single `PUSH`;
3. resolves a register PUSH through the existing finite all-path IA-32 register-provenance engine from `analyze_fun_00765470_body_owner_receiver.py`;
4. records memory/immediate/entry-register physical origins exactly;
5. fails closed on ambiguous, derived, unknown, or missing provenance.

It also records ECX provenance at the callsite because ECX is the physical receiver lane, but this phase does not use receiver continuity to invent semantics for the explicit source object.

## One-command runner

```bash
GHIDRA_HOME=/opt/ghidra \
  bash tools/ghidra/run_fun_007618f0_second_arg_provenance.sh \
  /home/pes/ghidra_projects/shift \
  shift \
  SHIFT.exe \
  out/shift_ghidra_database \
  out/fun_007618f0_second_arg
```

The runner first creates the finite caller worklist, then invokes the existing targeted instruction exporter only for those callers, then writes:

```text
fun_007618f0_second_arg_provenance.json
```

with format `SHIFT.Fun007618f0SecondArgumentProvenance/1`.

## Deliberate boundary

A physical argument origin such as `memory:[reg+offset]` or an entry-register continuity result still does not prove what object that storage represents. A positive Phase 738 retail report must be joined to an independent storage/object identity proof before the `+0x338/+0x918` fields can be internalized.

Until that retail report and owner join exist:

- `FUN_007618f0` second-source ownership remains external;
- Phase737 -> Phase728 -> Phase727 is not wired into the production complete `FUN_00765c40` anchor;
- the active top-level external-provider count remains seven.

## Regression

Synthetic regressions verify:

- direct-callgraph worklist selection excludes indirect edges;
- a register PUSH resolves through a prior memory load;
- entry-register continuity is preserved;
- non-immediate argument pushes fail closed;
- target drift at the callsite is rejected.
